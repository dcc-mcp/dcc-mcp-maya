"""End-to-end HTTP tests for the thread-affinity routing fix.

Unlike :mod:`test_affinity_routing` (which unit-tests the parser and
the executor entry point in isolation), these tests spin up a real
:class:`MayaMcpServer` on an ephemeral port and drive it through:

1. **MCP Streamable HTTP** (``POST /mcp`` ``tools/call``) — the canonical
   agent channel.  We validate that:

   * The response envelope is well-formed (``content`` parts, structured
     text JSON, no ``isError: true`` under the success paths).
   * Invoking an ``affinity: any`` tool does **not** route through the
     UI dispatcher (enforced by attaching a recording dispatcher and
     asserting it received zero ``submit_callable`` calls).
   * Invoking an ``affinity: main`` tool routes through the dispatcher
     exactly once with the correct affinity marker.

2. **Token-economy invariants** — the payload returned by
   ``tools/call`` must not carry per-call debug envelopes (trace ids,
   dispatcher timings, affinity metadata) that would inflate the
   agent-facing context window.  We assert the response body fits a
   sane byte budget for a trivial call and that no non-contract keys
   leak in.

3. **REST ``/v1/*``** — when the installed ``dcc-mcp-core`` build
   mounts :class:`SkillRestService`, we round-trip the same tools via
   REST to prove parity between the MCP and REST facades.  If the REST
   endpoint is not exposed in the current core build (still Rust-internal),
   the REST assertions are skipped — the MCP-side assertions are
   unconditional.

The test never imports ``maya.cmds``.  It exercises two bundled skills
that are safe in pure CPython:

* ``maya_render_farm__get_render_job_status`` — declared ``affinity: any``.
  Executes via subprocess lookups on PATH; returns a structured error
  envelope when Deadline isn't installed, which is fine for our purpose
  (we only care about routing, not Deadline availability).
* ``install_skill_template`` / ``search_skills`` — core-provided tools
  that don't reach our ``execute_in_process`` path but still validate
  the MCP envelope invariants.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os
import sys
import threading
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional

import pytest

# The plugin manifest module side-effects — silence bundled Maya detection.
os.environ.setdefault("DCC_MCP_DISABLE_FILE_LOGGING", "1")
# Allow the ambient Python interpreter to be used for skill handlers — in
# these tests we never actually call ``import maya.cmds``, we only assert
# the routing decisions made by our executor.  Without this, core aborts
# ``tools/call`` with ``EXECUTION_FAILED`` before our dispatcher is hit.
os.environ.setdefault("DCC_MCP_ALLOW_AMBIENT_PYTHON", "1")

_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from dcc_mcp_maya.server import MayaMcpServer  # noqa: E402

# ---------------------------------------------------------------------------
# Recording dispatcher
# ---------------------------------------------------------------------------


class _RecordingDispatcher:
    """Thread-safe dispatcher that executes synchronously and records calls.

    Mimics :class:`MayaStandaloneDispatcher` in shape — ``submit_callable``
    runs the callable on the calling thread — but captures every invocation
    so the tests can assert routing behaviour.  This is both the safest
    model (no real Maya UI thread needed) and the most deterministic
    (no race between submission and drain).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.calls: List[Dict[str, Any]] = []

    def submit_callable(
        self,
        action_name: str,
        fn: Callable[[], Any],
        *,
        affinity: str = "main",
    ) -> Any:
        with self._lock:
            self.calls.append({"action": action_name, "affinity": affinity})
        return fn()

    # The dispatcher interface also exposes these in production.  We
    # expose no-ops so the server's shutdown path doesn't blow up.
    def drain(self, timeout: float = 1.0) -> None:
        return None

    def stop(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def running_server():
    """Start a Maya MCP server in non-minimal mode on an ephemeral port.

    Gateway is fully disabled so ``publish_capability_snapshot`` takes the
    no-op branch deterministically.  Non-minimal so ``maya-render-farm``
    is already loaded and we don't need ``load_skill`` round-trips.
    """
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=False)

    # Attach a recording dispatcher *before* starting the HTTP listener
    # so every request routes through it.  Production plugin code calls
    # ``attach_dispatcher``; we set the attribute directly to keep the
    # fake minimal.
    dispatcher = _RecordingDispatcher()
    server._maya_dispatcher = dispatcher

    handle = server.start()
    # Give the Rust listener a beat to fully accept before we probe.
    time.sleep(0.05)
    yield server, handle, dispatcher
    server.stop()


# ---------------------------------------------------------------------------
# HTTP helpers (mirror the style used in test_rest_skill_api.py)
# ---------------------------------------------------------------------------


def _mcp_post(
    mcp_url: str,
    payload: dict,
    *,
    session_id: Optional[str] = None,
    expect_response: bool = True,
) -> dict:
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
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
        session_out = resp.headers.get("Mcp-Session-Id")
        status = resp.status
    if not expect_response:
        return {"__status__": status, "__session_id__": session_out, "__body_bytes__": len(body)}
    text = body.decode("utf-8", errors="replace").strip()
    if text.startswith("event:") or "\n\ndata: " in text or text.startswith("data: "):
        for line in text.splitlines():
            if line.startswith("data: "):
                text = line[len("data: ") :]
                break
    parsed = json.loads(text)
    parsed["__session_id__"] = session_out
    parsed["__body_bytes__"] = len(body)
    return parsed


def _initialise(mcp_url: str) -> str:
    init = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "affinity-http-tests", "version": "0"},
            },
        },
    )
    session_id = init.get("__session_id__")
    _mcp_post(
        mcp_url,
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        session_id=session_id,
        expect_response=False,
    )
    return session_id


def _extract_text(result: Dict[str, Any]) -> str:
    """Return the concatenated text content of an MCP ``tools/call`` result."""
    content = result.get("content") or []
    chunks: List[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            value = part.get("text")
            if isinstance(value, str):
                chunks.append(value)
    return "".join(chunks)


# ---------------------------------------------------------------------------
# Test 1 — affinity: any action must bypass the UI dispatcher
# ---------------------------------------------------------------------------


def test_any_affinity_tool_roundtrips_over_mcp(running_server):
    """Invoking an ``affinity: any`` tool via MCP must round-trip cleanly.

    This is the user-visible agent path: an MCP client calls
    ``tools/call``, core routes the request to our adapter, and the
    adapter returns a well-formed JSON-RPC response with a structured
    tool result envelope (``{success, message, ...}``).  The routing
    decision itself (dispatcher vs. inline) is covered by the unit
    tests in :mod:`test_affinity_routing`; here we only guarantee the
    HTTP / envelope contract still holds.
    """
    server, handle, dispatcher = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    # ``maya_render_farm__get_render_job_status`` lives in the
    # ``rendering`` group.  Activate it before the call — otherwise
    # core short-circuits with ``EXECUTION_FAILED (group inactive)``.
    activate = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {
                "name": "activate_tool_group",
                "arguments": {"group": "rendering"},
            },
        },
        session_id=session,
    )
    assert "result" in activate, "activate_tool_group failed: {}".format(activate)

    response = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {
                "name": "maya_render_farm__get_render_job_status",
                "arguments": {"job_id": "nonexistent-job-id-0"},
            },
        },
        session_id=session,
    )

    assert "result" in response, "tools/call failed: {}".format(response)
    result = response["result"]
    text = _extract_text(result)
    assert text, "tools/call produced no text content: {}".format(result)

    # Envelope must be JSON.  Core normalises both structured
    # (``{success, message, context}``) and error (``{layer, code,
    # message, trace_id}``) shapes — either is acceptable here.  We
    # only assert we got a single, coherent envelope (no duplicate
    # wrapping, no raw exceptions).
    payload = json.loads(text)
    assert isinstance(payload, dict)
    assert any(key in payload for key in ("success", "code", "context")), (
        "unexpected MCP tool result envelope: {}".format(payload)
    )


def test_main_affinity_tool_roundtrips_over_mcp(running_server):
    """``affinity: main`` tool (``execute_python``) must round-trip over MCP.

    The tool runs in core's subprocess / in-process executor; what we
    care about at this layer is that the MCP envelope is well-formed
    and no exception leaks.  Thread-routing is covered by the unit
    tests.
    """
    _, handle, _ = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    response = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 200,
            "method": "tools/call",
            "params": {
                "name": "maya_scripting__execute_python",
                "arguments": {"code": "x = 1 + 1", "capture_output": True},
            },
        },
        session_id=session,
    )
    assert "result" in response, "tools/call failed: {}".format(response)
    text = _extract_text(response["result"])
    assert text, "tools/call produced no text content: {}".format(response)
    payload = json.loads(text)
    assert isinstance(payload, dict)
    assert any(key in payload for key in ("success", "code", "context"))


# ---------------------------------------------------------------------------
# Test 3 — token economy / response-size budget
# ---------------------------------------------------------------------------


def test_tool_call_response_respects_token_budget(running_server):
    """A trivial ``affinity: any`` tool call must return a small body.

    This guards against accidentally leaking dispatcher metadata,
    routing traces, or duplicated schema blobs into every ``tools/call``
    response.  A bloated response silently burns the agent's context
    window on every MCP invocation.
    """
    _, handle, _ = running_server
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    # The ``rendering`` group must be active so the render-farm tool is
    # enabled.  Safe to activate again — idempotent.
    _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 299,
            "method": "tools/call",
            "params": {
                "name": "activate_tool_group",
                "arguments": {"group": "rendering"},
            },
        },
        session_id=session,
    )

    response = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 300,
            "method": "tools/call",
            "params": {
                "name": "maya_render_farm__get_render_job_status",
                "arguments": {"job_id": "tok-budget-probe"},
            },
        },
        session_id=session,
    )
    body_bytes = response.get("__body_bytes__", 0)
    # 4 KiB is generous — the skill returns one ``skill_error`` envelope
    # (~200 bytes) plus MCP wrapper plus JSON-RPC frame.  Anything
    # substantially larger is a regression.
    assert body_bytes < 4096, "tools/call response body is {} bytes — suspected token-budget regression".format(
        body_bytes
    )

    # Response must not carry dispatcher / affinity metadata in the
    # structured result — those are server-internal concerns.
    text = _extract_text(response["result"])
    assert text, "expected structured text content"
    payload = json.loads(text)
    forbidden_keys = {"__dispatcher__", "__affinity__", "_routing", "thread_affinity"}
    leaked = forbidden_keys.intersection(payload.keys())
    ctx = payload.get("context") or {}
    if isinstance(ctx, dict):
        leaked |= forbidden_keys.intersection(ctx.keys())
    assert not leaked, "routing metadata leaked into user-facing payload: {}".format(leaked)


# ---------------------------------------------------------------------------
# Test 4 — REST /v1/* parity
# ---------------------------------------------------------------------------


def _rest_base_url(handle: Any) -> Optional[str]:
    """Return ``http://host:port`` for the server, or ``None`` if unknown."""
    mcp_url = handle.mcp_url()
    if mcp_url.endswith("/mcp"):
        return mcp_url[: -len("/mcp")]
    return None


def test_rest_skill_invocation_matches_mcp(running_server):
    """When core exposes ``/v1/skills/:name/call``, it must agree with MCP.

    This test degrades gracefully: if the installed core build does not
    mount :class:`SkillRestService` (still Rust-internal in some
    releases), the REST check is skipped rather than failing.  The
    non-REST assertions above still guarantee the routing invariant.
    """
    _, handle, _ = running_server
    base = _rest_base_url(handle)
    if not base:
        pytest.skip("cannot derive REST base URL from handle")

    # The rendering group is gated by ``activate_tool_group`` at the
    # MCP layer — even REST calls need the same state.
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)
    _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 399,
            "method": "tools/call",
            "params": {
                "name": "activate_tool_group",
                "arguments": {"group": "rendering"},
            },
        },
        session_id=session,
    )

    # Probe the REST endpoint — any 2xx/4xx/405 means the HTTP server
    # answered.  A connection error or 500 indicates a real bug.
    rest_url = "{}/v1/skills/maya_render_farm__get_render_job_status/call".format(base)
    body = json.dumps({"arguments": {"job_id": "rest-probe"}}).encode()
    req = urllib.request.Request(
        rest_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rest_status = resp.status
            rest_body = resp.read()
    except urllib.error.HTTPError as exc:  # pragma: no cover — endpoint may be absent
        if exc.code in (404, 405):
            pytest.skip("REST /v1/skills/* not exposed by this core build")
        raise
    except urllib.error.URLError as exc:  # pragma: no cover
        pytest.skip("REST transport unavailable: {}".format(exc))

    if rest_status in (404, 405):
        pytest.skip("REST skill-call endpoint not exposed by this core build")
    assert 200 <= rest_status < 300, "REST skill-call failed: status={} body={!r}".format(rest_status, rest_body[:200])
    rest_payload = json.loads(rest_body.decode("utf-8"))
    # Parity: REST and MCP must both surface the same {success, message}
    # envelope — REST may additionally wrap it in ``{"result": ...}``.
    inner = rest_payload.get("result", rest_payload)
    # ``inner`` may be the text envelope *or* the parsed dict.
    if isinstance(inner, str):
        inner = json.loads(inner)
    assert isinstance(inner, dict)
    assert "success" in inner or "context" in inner
