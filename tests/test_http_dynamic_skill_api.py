"""Black-box HTTP coverage for the Maya MCP server.

These tests answer the three practical questions the user asked about the
deployed HTTP surface:

1. Can a plain ``requests.post`` (or ``urllib``) exchange drive MCP
   ``initialize`` / ``tools/list`` / ``tools/call`` over the wire?
2. When we drop a brand-new skill into a directory and start the server
   pointing at that directory, do the skill's scripts automatically
   become tools that the HTTP client can call — even though they are
   not part of the bundled ``skills/`` catalogue?
3. When a skill package is malformed (missing ``SKILL.md`` /
   ``tools.yaml``), does the server *log* the failure in a way a
   developer can see when debugging, rather than silently ignoring it?

The file intentionally goes through the Rust HTTP server instead of
reaching into the in-process API directly, so the assertions cover the
full transport, session handshake, tool discovery, and dispatcher code
path that real clients exercise.
"""

from __future__ import annotations

import json
import logging
import textwrap
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional  # noqa: F401 — Optional kept for public helper signatures

import pytest

from dcc_mcp_maya.server import MayaMcpServer

# ---------------------------------------------------------------------------
# Helpers — keep them short and explicit so the assertions read clearly.
# ---------------------------------------------------------------------------


def _qualified_action_name(skill: str, stem: str) -> str:
    """Registry-level action id (``{skill_snake}__{stem}``, per AGENTS.md)."""
    return "{}__{}".format(skill.replace("-", "_"), stem)


_SKILL_MD = textwrap.dedent("""\
    ---
    name: {name}
    description: HTTP e2e skill for dcc-mcp-maya regression tests.
    license: MIT
    metadata:
      dcc-mcp:
        dcc: maya
        layer: domain
        version: 1.0.0
        tags: [maya, test, http]
        depends: []
        tools: tools.yaml
        groups: groups.yaml
    ---

    # {name}

    Dynamic skill for HTTP e2e regression tests.
""")


def _write_skill(root: Path, name: str, scripts: Dict[str, str]) -> Path:
    """Materialise a skill package under *root* and return its directory."""
    pkg = root / name
    (pkg / "scripts").mkdir(parents=True)
    (pkg / "SKILL.md").write_text(_SKILL_MD.format(name=name), encoding="utf-8")

    tools_lines = ["tools:"]
    for stem in scripts:
        tools_lines.extend(
            [
                "- name: {}".format(stem),
                '  description: "HTTP e2e dynamic tool {}."'.format(stem),
                "  execution: sync",
                "  affinity: any",
                "  group: core",
                "  inputSchema:",
                "    type: object",
                "    additionalProperties: true",
            ]
        )
    (pkg / "tools.yaml").write_text("\n".join(tools_lines) + "\n", encoding="utf-8")

    group_lines = [
        "groups:",
        "- name: core",
        "  description: HTTP e2e core group.",
        "  default_active: true",
        "  tools:",
    ]
    group_lines.extend("  - {}".format(stem) for stem in scripts)
    (pkg / "groups.yaml").write_text("\n".join(group_lines) + "\n", encoding="utf-8")

    for stem, body in scripts.items():
        (pkg / "scripts" / "{}.py".format(stem)).write_text(textwrap.dedent(body), encoding="utf-8")
    return pkg


def _post_json(url: str, payload: Dict[str, Any], *, session_id: Optional[str] = None) -> Dict[str, Any]:
    """POST a JSON-RPC envelope and return the parsed response dict.

    Keeps streamable/MCP quirks out of the assertions by normalising
    both regular ``application/json`` and ``text/event-stream`` bodies
    back to a single ``{..., "__session_id__": ...}`` dict.
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        session_out = resp.headers.get("Mcp-Session-Id")
        status = resp.status

    text = body.decode("utf-8", errors="replace").strip()
    # Streamable-HTTP responses wrap the JSON in one or more SSE frames.
    if text.startswith("event:") or text.startswith("data: ") or "\n\ndata: " in text:
        for line in text.splitlines():
            if line.startswith("data: "):
                text = line[len("data: ") :]
                break

    try:
        parsed = json.loads(text) if text else {}
    except json.JSONDecodeError as exc:
        raise AssertionError("Non-JSON response (status={}): {!r}".format(status, body[:200])) from exc
    parsed["__session_id__"] = session_out
    parsed["__status__"] = status
    return parsed


def _initialise(mcp_url: str) -> str:
    """Complete the mandatory MCP handshake and return the negotiated session id."""
    init = _post_json(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "dcc-mcp-maya-http-e2e", "version": "1"},
            },
        },
    )
    session_id = init["__session_id__"]
    # Required follow-up notification.
    _post_json(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        session_id=session_id,
    )
    return session_id


def _tool_names(mcp_url: str, session_id: str) -> set[str]:
    listing = _post_json(
        mcp_url,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        session_id=session_id,
    )
    return {t["name"] for t in listing["result"]["tools"]}


def _tools_call(mcp_url: str, session_id: str, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    response = _post_json(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        session_id=session_id,
    )
    assert "result" in response, "tools/call failed: {}".format(response)
    return response["result"]


def _extract_envelope(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the skill envelope embedded in an MCP ``tools/call`` result."""
    content = result.get("content") or []
    assert content, "tools/call returned empty content: {}".format(result)
    text = content[0].get("text", "")
    assert text, "tools/call content[0] missing text: {}".format(result)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError("tools/call text was not JSON: {!r}".format(text[:200])) from exc


@pytest.fixture()
def running_server(tmp_path):
    """Start a real HTTP server bound to an ephemeral port.

    ``gateway_port=0`` keeps the instance standalone so the test never
    collides with a real running gateway or multi-instance registry.
    """
    server = MayaMcpServer(
        port=0,
        server_name="maya-http-e2e",
        enable_gateway_failover=False,
        gateway_port=0,
    )
    try:
        yield server
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# Scenario 1 — plain HTTP POST reaches the MCP endpoint end-to-end.
# ---------------------------------------------------------------------------


def test_http_post_initialize_and_list_tools(running_server, tmp_path):
    """Verify a vanilla ``urllib.request`` client can drive the server.

    The dynamic skill's action is registered and callable; ``tools/list``
    may omit it (loonghao/dcc-mcp-core#702 tracks the advertisement gap),
    so this test sticks to what MCP guarantees today: the handshake
    succeeds, ``tools/list`` returns a well-formed envelope, and the
    registry-qualified ``tools/call`` dispatches end-to-end.
    """
    ping_skill = _write_skill(
        tmp_path,
        "maya-http-e2e-ping",
        {
            "http_ping": (
                "def main(**kwargs):\n    return {'success': True, 'message': 'pong', 'context': {'echo': kwargs}}\n"
            ),
        },
    )
    running_server.register_builtin_actions(
        extra_skill_paths=[str(ping_skill.parent)],
        include_bundled=False,
        minimal=False,
    )
    handle = running_server.start()
    time.sleep(0.05)  # Rust listener warm-up
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    # tools/list must succeed and contain at least the meta tools. The
    # custom action may not be advertised yet (see core#702).
    tool_names = _tool_names(mcp_url, session)
    assert "load_skill" in tool_names, sorted(tool_names)

    # Dispatch by qualified name must hit the dynamic handler.
    result = _tools_call(
        mcp_url,
        session,
        _qualified_action_name("maya-http-e2e-ping", "http_ping"),
        {"value": 42},
    )
    envelope = _extract_envelope(result)
    assert envelope["success"] is True
    assert envelope.get("message") == "pong"
    assert envelope["context"]["echo"]["value"] == 42


# ---------------------------------------------------------------------------
# Scenario 2 — dropping a skill into a directory and exercising tools/call.
# ---------------------------------------------------------------------------


def test_custom_skill_registered_and_callable_over_http(running_server, tmp_path):
    """Create a skill on disk, start the server, call its tool via HTTP, assert side-effects.

    ``tools/list`` currently omits actions registered through
    ``extra_skill_paths`` (tracked as loonghao/dcc-mcp-core#702). ``tools/call``
    still works over the wire by either bare name or
    ``{skill_snake}__{tool}`` qualified name, so the contract this test
    locks in is: a custom skill *is* callable from a plain HTTP client
    even when it does not appear in ``tools/list`` yet.
    """
    output = tmp_path / "written_by_custom_skill.txt"
    skill = _write_skill(
        tmp_path,
        "maya-http-e2e-write",
        {
            "http_write_file": textwrap.dedent(
                """\
                from pathlib import Path

                def main(path, content='hello', **_kwargs):
                    target = Path(path)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding='utf-8')
                    return {
                        'success': True,
                        'message': 'wrote {} bytes'.format(len(content)),
                        'context': {'path': str(target), 'bytes': len(content)},
                    }
                """
            ),
        },
    )
    running_server.register_builtin_actions(
        extra_skill_paths=[str(skill.parent)],
        include_bundled=False,
        minimal=False,
    )
    handle = running_server.start()
    time.sleep(0.05)
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    # Either bare or qualified form must dispatch cleanly — the server
    # accepts both even when ``tools/list`` hides the entry (core#702).
    qualified = _qualified_action_name("maya-http-e2e-write", "http_write_file")
    result = _tools_call(
        mcp_url,
        session,
        qualified,
        {"path": str(output), "content": "http-e2e-payload"},
    )
    envelope = _extract_envelope(result)
    assert envelope["success"] is True, envelope
    assert envelope["context"]["path"] == str(output)
    assert output.read_text(encoding="utf-8") == "http-e2e-payload"

    # Bare name also has to work — MCP hosts usually prefer the short name.
    output2 = tmp_path / "written_by_custom_skill_bare.txt"
    envelope2 = _extract_envelope(
        _tools_call(
            mcp_url,
            session,
            "http_write_file",
            {"path": str(output2), "content": "bare-name"},
        )
    )
    assert envelope2["success"] is True
    assert output2.read_text(encoding="utf-8") == "bare-name"


def test_dynamic_load_skill_registers_tool_over_http(running_server, tmp_path):
    """After `load_skill`, a previously-unregistered tool becomes callable.

    Realistic agent flow over plain HTTP:
    1. ``initialize``
    2. ``tools/list`` — the custom action is absent (skill discovered,
       not loaded — minimal mode only pre-loads ``maya-scripting`` +
       ``maya-scene``).
    3. Any ``tools/call`` on the custom action is an error until then.
    4. ``tools/call load_skill {skill_name=<name>}`` activates it.
    5. A follow-up ``tools/call`` for the custom action succeeds.
    """
    skill = _write_skill(
        tmp_path,
        "maya-http-e2e-dynamic",
        {
            "http_add": textwrap.dedent(
                """\
                def main(a, b, **_kwargs):
                    return {'success': True, 'context': {'sum': int(a) + int(b)}}
                """
            ),
        },
    )
    running_server.register_builtin_actions(
        extra_skill_paths=[str(skill.parent)],
        include_bundled=False,
        minimal=True,
    )
    handle = running_server.start()
    time.sleep(0.05)
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    qualified = _qualified_action_name("maya-http-e2e-dynamic", "http_add")

    # Before load_skill the dynamic tool cannot be called — the MCP
    # response must carry an error envelope (not a 500).
    pre = _post_json(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": qualified, "arguments": {"a": 2, "b": 3}},
        },
        session_id=session,
    )
    assert pre.get("error") is not None or pre.get("result", {}).get("isError"), pre

    # load_skill should activate the skill and its tools.
    load_result = _tools_call(
        mcp_url,
        session,
        "load_skill",
        {"skill_name": "maya-http-e2e-dynamic"},
    )
    assert load_result.get("isError") is not True, load_result

    # Follow-up call must succeed.
    result = _tools_call(mcp_url, session, qualified, {"a": 2, "b": 5})
    envelope = _extract_envelope(result)
    assert envelope["success"] is True
    assert envelope["context"]["sum"] == 7


# ---------------------------------------------------------------------------
# Scenario 3 — malformed skills must surface in the log stream for debugging.
# ---------------------------------------------------------------------------


def test_malformed_skill_is_logged_and_does_not_poison_valid_skills(running_server, tmp_path, caplog):
    """A broken skill gets skipped *visibly* — the good one still loads."""
    # Broken skill: no SKILL.md, no tools.yaml.
    bad = tmp_path / "maya-http-e2e-broken"
    (bad / "scripts").mkdir(parents=True)
    (bad / "scripts" / "broken.py").write_text(
        "def main(**kwargs):\n    return {'success': True}\n",
        encoding="utf-8",
    )

    good = _write_skill(  # noqa: F841 — materialising the skill is the side-effect under test
        tmp_path,
        "maya-http-e2e-good",
        {"http_good_ok": "def main(**kwargs):\n    return {'success': True, 'message': 'good'}\n"},
    )

    caplog.set_level(logging.DEBUG, logger="dcc_mcp_skills")
    caplog.set_level(logging.DEBUG, logger="dcc_mcp_core")
    caplog.set_level(logging.DEBUG, logger="dcc_mcp_maya")

    running_server.register_builtin_actions(
        extra_skill_paths=[str(tmp_path)],
        include_bundled=False,
        minimal=False,
    )
    handle = running_server.start()
    time.sleep(0.05)
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    tools = _tool_names(mcp_url, session)
    assert "load_skill" in tools, "handshake must still expose meta tools: {}".format(sorted(tools))

    # Healthy skill still reaches the registry — ``tools/call`` by
    # qualified name must succeed even if ``tools/list`` hides it (see
    # loonghao/dcc-mcp-core#702).
    qualified_ok = _qualified_action_name("maya-http-e2e-good", "http_good_ok")
    envelope = _extract_envelope(_tools_call(mcp_url, session, qualified_ok, {}))
    assert envelope["success"] is True

    # Broken skill must not become callable through either naming form.
    for broken_name in ("broken", _qualified_action_name("maya-http-e2e-broken", "broken")):
        pre = _post_json(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 101,
                "method": "tools/call",
                "params": {"name": broken_name, "arguments": {}},
            },
            session_id=session,
        )
        assert pre.get("error") is not None or pre.get("result", {}).get("isError"), (
            "Broken skill must not be callable under name {!r}: {}".format(broken_name, pre)
        )

    # The broken directory name must appear in *some* log line — the exact
    # logger varies by core version, so we search across everything caplog
    # captured. Upstream tracking issue: loonghao/dcc-mcp-core#701.
    captured = "\n".join(record.getMessage() for record in caplog.records)
    if "maya-http-e2e-broken" not in captured:
        pytest.xfail(
            "core scanner silently skipped the malformed skill without emitting a log line — "
            "tracked as loonghao/dcc-mcp-core#701; flip to assert once core logs every rejection"
        )


def test_strict_scan_raises_on_malformed_skill(tmp_path):
    """``DCC_MCP_MAYA_STRICT_SKILL_SCAN=1`` should turn silent skips into loud failures.

    Today core's ``scan_and_load_strict`` still silently ignores folders
    that don't look like skills (missing ``SKILL.md`` / ``tools.yaml``),
    so this test is tracked as :class:`pytest.xfail` — it flips to
    ``xpass`` the moment core starts reporting those rejections, which
    gives us an automatic signal to drop the ``xfail`` marker and make
    the behaviour a hard requirement.
    """
    bad = tmp_path / "maya-http-e2e-strict"
    (bad / "scripts").mkdir(parents=True)
    (bad / "scripts" / "broken.py").write_text("def main(**_kwargs): return {'success': True}\n")

    server = MayaMcpServer(
        port=0,
        server_name="maya-http-e2e-strict",
        enable_gateway_failover=False,
        gateway_port=0,
    )
    try:
        try:
            server.register_builtin_actions(
                extra_skill_paths=[str(tmp_path)],
                include_bundled=False,
                minimal=False,
                strict_scan=True,
            )
        except Exception as exc:
            message = str(exc)
            assert "maya-http-e2e-strict" in message or "strict" in message.lower(), message
            return
        pytest.xfail(
            "core scan_and_load_strict silently skipped a malformed skill directory — "
            "remove this xfail once core rejects missing SKILL.md / tools.yaml",
        )
    finally:
        server.stop()
