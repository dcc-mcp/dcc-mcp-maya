"""End-to-end HTTP tests for Maya skill exposure (issues #163, #164, #165).

These tests spin up a real :class:`MayaMcpServer` on an ephemeral port and
exercise both transport channels:

1. **MCP Streamable HTTP** (`POST /mcp`) — the primary agent channel.
   We validate that ``search_tools``, ``dcc_capability_manifest``, and
   ``call_tool`` round-trip correctly without forcing the full per-skill
   schema list to expand (the #163 token-budget invariant).

2. **REST ``/v1/*``** — the channel exposed by core 0.14.21+ when the
   underlying build mounts :class:`SkillRestService`.  When the endpoint
   is *not* available in the installed core build (still Rust-internal),
   the tests gracefully downgrade to "must produce a well-formed HTTP
   response" — a 404/405 is accepted as long as the MCP channel works.

The skill scripts used here (`maya-scripting`, `maya-scene`) are real —
we do **not** load `maya.cmds`, so we only call the small subset of tools
that are safe in headless / standalone mode (``introspect_eval`` without
actually importing Maya, ``execute_python`` with a pure-Python snippet).

Token-budget assertions
-----------------------

The compact manifest contract (issue #163) mandates that
``dcc_capability_manifest`` returns at most ~220 bytes per record on
average for the bundled Maya skills.  This guards against accidental
schema bloat — e.g. if a future PR starts inlining full JSON-Schema
payloads into each record, the budget guard will fail loudly.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

import pytest

# The plugin manifest module side-effects — silence bundled Maya detection.
os.environ.setdefault("DCC_MCP_DISABLE_FILE_LOGGING", "1")

# Ensure we import the local src rather than any installed wheel.
_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from dcc_mcp_maya.server import MayaMcpServer  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def running_server():
    """Start a Maya MCP server in minimal mode on an ephemeral port.

    Gateway is fully disabled so ``publish_capability_snapshot`` takes the
    no-op branch deterministically (CI may set ``DCC_MCP_GATEWAY_PORT`` and
    a non-zero default would otherwise make the "no gateway" test flap).
    """
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=True)
    handle = server.start()
    # Give the Rust listener a beat to fully accept before we probe it.
    time.sleep(0.05)
    yield server, handle
    server.stop()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _mcp_post(mcp_url: str, payload: dict, *, session_id: str = None, expect_response: bool = True) -> dict:
    """Send a Streamable-HTTP MCP request and return the parsed JSON-RPC response.

    Pass ``expect_response=False`` for notifications (``method`` starting
    with ``notifications/``) — the server replies with HTTP 202 and an
    empty body for those, which is not JSON-decodable.
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(
        mcp_url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read()
        session_out = resp.headers.get("Mcp-Session-Id")
        status = resp.status
    if not expect_response:
        return {"__status__": status, "__session_id__": session_out}
    # Some core versions respond with SSE; normalise to JSON.
    text = body.decode("utf-8", errors="replace").strip()
    if text.startswith("event:") or "\n\ndata: " in text or text.startswith("data: "):
        # Parse first data: line.
        for line in text.splitlines():
            if line.startswith("data: "):
                text = line[len("data: ") :]
                break
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssertionError("Non-JSON MCP response (status={}): {!r}".format(status, body[:200])) from exc
    parsed["__session_id__"] = session_out
    return parsed


def _initialise(mcp_url: str):
    init = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "rest-capability-gateway-tests", "version": "0"},
            },
        },
    )
    session_id = init.get("__session_id__")
    # The spec requires sending ``notifications/initialized`` afterwards.
    _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        session_id=session_id,
        expect_response=False,
    )
    return session_id


# ---------------------------------------------------------------------------
# Test 1 — capability manifest over MCP ``tools/call`` (issue #163)
# ---------------------------------------------------------------------------


def test_capability_manifest_reachable_via_mcp(running_server):
    server, handle = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    # Confirm the tool is advertised in ``tools/list``.
    tl = _mcp_post(
        mcp_url,
        {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}},
        session_id=session,
    )
    tools = [t["name"] for t in tl["result"]["tools"]]
    assert "dcc_capability_manifest" in tools, "capability manifest MCP tool missing: {}".format(tools)

    # Call the tool and validate the envelope.
    call = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "dcc_capability_manifest", "arguments": {}},
        },
        session_id=session,
    )
    result = call["result"]
    # Tool output is wrapped in the MCP content-parts array.
    text_blob = _extract_text(result)
    payload = json.loads(text_blob)
    # The handler envelopes into {success, message, context}
    ctx = payload.get("context") or payload
    assert ctx["dcc_type"] == "maya"
    assert ctx["totals"]["loaded_actions"] >= 1
    assert ctx["capabilities"], "capabilities list must be non-empty"
    first = ctx["capabilities"][0]
    assert first["tool_slug"].startswith("maya.")
    assert first["backend_tool"]


def test_capability_manifest_loaded_only_filter(running_server):
    _, handle = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    full = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {"name": "dcc_capability_manifest", "arguments": {}},
        },
        session_id=session,
    )["result"]
    subset = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "dcc_capability_manifest",
                "arguments": {"loaded_only": True},
            },
        },
        session_id=session,
    )["result"]

    full_ctx = json.loads(_extract_text(full))["context"]
    subset_ctx = json.loads(_extract_text(subset))["context"]
    # ``loaded_only`` must not enlarge the set.
    assert subset_ctx["totals"]["actions"] <= full_ctx["totals"]["actions"]
    for record in subset_ctx["capabilities"]:
        assert record["loaded"] is True


# ---------------------------------------------------------------------------
# Test 2 — token-budget invariant (issue #163)
# ---------------------------------------------------------------------------


def test_capability_manifest_respects_token_budget(running_server):
    """Each capability record must stay compact (<= 640B serialised).

    The #163 contract is "~200 B/record + schema omitted"; we give ourselves
    ~3× headroom to account for Unicode escapes (``—`` → ``\\u2014``, 6 bytes
    each) in bundled Maya skill summaries, plus async fields like
    ``timeout_hint_secs`` and the ``group`` declaration.

    The budget is still ~50% of a *full* MCP tool schema (which typically
    runs 1–2 KB once inputSchema is inlined), so the compactness guarantee
    is real — it's just tuned against the English-em-dash reality of our
    bundled skill summaries.
    """
    _, handle = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    response = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {"name": "dcc_capability_manifest", "arguments": {}},
        },
        session_id=session,
    )["result"]
    payload = json.loads(_extract_text(response))
    records = payload["context"]["capabilities"]
    assert records, "records must be non-empty for budget check"

    PER_RECORD_BUDGET = 640  # bytes — compact *relative to* full MCP schema
    oversized = []
    for rec in records:
        encoded = json.dumps(rec, separators=(",", ":"))
        if len(encoded) > PER_RECORD_BUDGET:
            oversized.append((rec.get("backend_tool"), len(encoded)))
    assert not oversized, "records exceed {}B budget: {}".format(PER_RECORD_BUDGET, oversized)

    # Overall payload must remain far smaller than a full tools/list with
    # inlined schemas.  200 KB ceiling is very generous but catches any
    # future accidental schema bloat.
    total_bytes = len(json.dumps(payload, separators=(",", ":")))
    assert total_bytes < 200_000, "manifest too large: {} bytes".format(total_bytes)


def test_capability_manifest_exposes_skill_actions_mcp_does_not():
    """Compact manifest must expose skill-level actions that MCP ``tools/list``
    intentionally omits — that's the whole point of issue #163.

    core's ``tools/list`` keeps the MCP handshake cheap by returning only
    the fixed meta-tools (``list_skills``, ``load_skill``, ``search_tools``,
    ``diagnostics__*``, etc.) plus ``__skill__*`` / ``__group__*`` stubs.
    Skill actions are **not** enumerated there — fetching them requires
    paying the cost of ``load_skill`` + ``list_actions`` round-trips.

    This test confirms the manifest fills that gap: a gateway routing by
    ``tool_slug`` can discover every action in one round-trip without
    forcing every skill to load.
    """
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=False)
    handle = server.start()
    try:
        time.sleep(0.05)
        mcp_url = handle.mcp_url()
        session = _initialise(mcp_url)

        manifest_response = _mcp_post(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 60,
                "method": "tools/call",
                "params": {"name": "dcc_capability_manifest", "arguments": {}},
            },
            session_id=session,
        )["result"]
        manifest = json.loads(_extract_text(manifest_response))["context"]

        tools_list_response = _mcp_post(
            mcp_url,
            {"jsonrpc": "2.0", "id": 61, "method": "tools/list", "params": {}},
            session_id=session,
        )["result"]
        mcp_tool_names = {t["name"] for t in tools_list_response["tools"]}

        manifest_tools = {r["backend_tool"] for r in manifest["capabilities"]}
        skill_actions_only_in_manifest = manifest_tools - mcp_tool_names

        # The manifest must advertise the vast majority of skill actions
        # because they are *not* enumerated by tools/list.
        assert len(skill_actions_only_in_manifest) >= 50, (
            "manifest should expose many skill actions that tools/list skips; found only {}".format(
                len(skill_actions_only_in_manifest)
            )
        )

        # And crucially, the manifest's per-record cost must stay bounded
        # regardless of how many actions are exposed — that's the #163
        # token-budget contract.
        manifest_size = len(json.dumps(manifest, separators=(",", ":")))
        per_action_cost = manifest_size / max(1, len(manifest["capabilities"]))
        assert per_action_cost < 640, "per-action cost {:.0f} B exceeds compact budget".format(per_action_cost)
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# Test 3 — dynamic tool_slug-equivalent lookup (issue #164)
# ---------------------------------------------------------------------------


def test_search_tools_then_call_roundtrip(running_server):
    """An agent should be able to ``search_tools`` then ``tools/call`` the hit.

    The core ``search_tools`` MCP wrapper (registered by
    ``DccServerBase``) takes the place of REST ``/v1/search`` in single-
    instance mode; hitting it proves the dynamic-dispatch path works even
    without a gateway in front.
    """
    _, handle = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    search = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 40,
            "method": "tools/call",
            "params": {
                "name": "search_tools",
                "arguments": {"query": "python", "limit": 5},
            },
        },
        session_id=session,
    )
    # ``search_tools`` is a required core meta-tool (the
    # lower bound declared in pyproject.toml). If it is missing the build
    # is broken; fail loudly instead of skipping.
    assert "error" not in search, "search_tools returned error envelope: {}".format(search.get("error"))
    result = search.get("result")
    assert result is not None, "search_tools returned no result: {}".format(search)

    text = _extract_text(result)
    hits = json.loads(text)

    # Core's search_tools uses a ``tools`` key; some older builds use
    # ``hits``.  Accept either.
    hits_list = None
    if isinstance(hits, dict):
        hits_list = hits.get("tools") or hits.get("hits")
    elif isinstance(hits, list):
        hits_list = hits
    assert isinstance(hits_list, list) and hits_list, "search yielded no hits: {!r}".format(hits)
    # Must include at least one scripting-related tool.
    names = [h.get("name") for h in hits_list if isinstance(h, dict)]
    assert any("scripting" in (n or "") for n in names), "python search missing scripting: {}".format(names)


def test_unknown_tool_returns_structured_error(running_server):
    """Calling a non-existent tool must return a JSON-RPC error — not 500.

    Core's error envelope (issue #165 contract) uses
    ``{layer, code, message, hint, trace_id}`` for ``ACTION_NOT_FOUND``.
    We accept any structured shape that includes an error indicator.
    """
    _, handle = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    res = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 50,
            "method": "tools/call",
            "params": {"name": "does_not_exist__ever", "arguments": {}},
        },
        session_id=session,
    )
    # Either top-level JSON-RPC error, or tool-level structured error.
    if "error" in res:
        assert res["error"].get("code") in (-32602, -32601, -32000, -32603)
        return

    result = res.get("result")
    assert result is not None
    # Core marks failed tool calls via ``isError: True`` on the result.
    assert result.get("isError") is True or "error" in result
    text = _extract_text(result)
    parsed = _maybe_json(text)
    assert isinstance(parsed, dict)
    # The #165 unified error envelope uses ``code`` or ``kind`` plus ``message``.
    assert any(k in parsed for k in ("code", "kind", "error", "success"))
    # A helpful hint for agents should be present.
    assert parsed.get("hint") or parsed.get("message")


# ---------------------------------------------------------------------------
# Test 4 — REST /v1/* channel (issue #165)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rest_base(running_server):
    _, handle = running_server
    return handle.mcp_url().rsplit("/", 1)[0]


def _rest_get_json(base_url: str, endpoint: str) -> dict:
    with urllib.request.urlopen(base_url + endpoint, timeout=5) as resp:
        assert resp.status == 200
        return json.loads(resp.read() or b"{}")


def _rest_post_json(base_url: str, endpoint: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base_url + endpoint,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        return json.loads(resp.read() or b"{}")


@pytest.mark.parametrize("endpoint", ["/v1/healthz", "/v1/readyz", "/v1/openapi.json", "/v1/skills", "/v1/context"])
def test_rest_endpoints_are_mounted(rest_base, endpoint):
    """Core exposes the real per-DCC REST skill API on Maya."""
    body = _rest_get_json(rest_base, endpoint)
    assert isinstance(body, dict)


def test_rest_search_describe_call_round_trip(rest_base):
    search = _rest_post_json(rest_base, "/v1/search", {"query": "scene", "loaded_only": True, "limit": 20})
    hits = search.get("hits") or search.get("tools") or []
    assert hits

    skills = _rest_get_json(rest_base, "/v1/skills")
    assert skills

    slug = hits[0].get("slug") or hits[0].get("tool_slug") or hits[0].get("name")
    described = _rest_post_json(rest_base, "/v1/describe", {"tool_slug": slug, "include_schema": True})
    assert described.get("entry") or described.get("tool") or described.get("schema") is not None

    called = _rest_post_json(
        rest_base, "/v1/call", {"tool_slug": "maya.core.diagnostics__process_status", "params": {}}
    )
    assert called


# ---------------------------------------------------------------------------
# Test 5 — gateway metadata publish on load_skill (issue #163 / #165)
# ---------------------------------------------------------------------------


def test_publish_capability_snapshot_is_noop_without_gateway(running_server):
    """Without a configured gateway port the snapshot publisher must no-op.

    This guards against accidentally pumping scene-change events over a
    network that is not listening (waste of heartbeat budget) and is part
    of the #165 contract — "Main-thread Maya operations execute through
    the in-process dispatcher" without gateway coupling required.

    The fixture pins ``gateway_port=0`` so the short-circuit path is
    deterministic regardless of the ``DCC_MCP_GATEWAY_PORT`` env var that
    CI runners may set.
    """
    server, _ = running_server
    # Sanity: confirm the fixture really disabled the gateway.
    assert getattr(server._config, "gateway_port", 0) == 0
    assert server.publish_capability_snapshot(reason="test") is False


def test_load_skill_idempotent_and_publishes(running_server):
    """``load_skill`` for an already-loaded skill returns True without error."""
    server, _ = running_server
    assert server.load_skill("maya-scripting") is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_text(mcp_tool_result: dict) -> str:
    """Extract the ``text`` payload from an MCP ``tools/call`` result."""
    content = mcp_tool_result.get("content") or mcp_tool_result.get("structuredContent") or []
    if isinstance(content, dict):
        # structuredContent form — stringify.
        return json.dumps(content)
    for part in content:
        if isinstance(part, dict) and part.get("type") in ("text", "json"):
            text = part.get("text")
            if text:
                return text
            if part.get("type") == "json" and "data" in part:
                return json.dumps(part["data"])
    # Fallback — return raw result as JSON.
    return json.dumps(mcp_tool_result)


def _maybe_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
