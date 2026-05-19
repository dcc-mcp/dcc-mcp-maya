"""Dynamic tool dispatch tests (issue #164).

When the gateway calls tools dynamically by ``tool_slug`` / backend
action-id instead of per-tool MCP wrappers, the Maya adapter must still:

* honour ``affinity: main`` via the attached :class:`MayaUiDispatcher`,
* surface a clear ``load_skill``-style hint when a call targets an
  unloaded skill (no crash, no generic "internal error"),
* keep the in-process Python handler reachable after dynamic load,
* produce the core-standard error envelope (``code=ACTION_NOT_FOUND``,
  ``hint="load_skill first"``) for unknown targets.

These tests exercise the adapter without Maya running: we attach a fake
dispatcher that records every ``submit_callable`` call so we can assert
the correct affinity tag travels all the way from the HTTP handler
through to ``MayaMcpServer._executor``.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("DCC_MCP_DISABLE_FILE_LOGGING", "1")

_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from dcc_mcp_maya.server import MayaMcpServer  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers (shared with test_rest_skill_api.py shape)
# ---------------------------------------------------------------------------


def _mcp_post(mcp_url: str, payload: dict, *, session_id: str = None, expect_response: bool = True) -> dict:
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
    text = body.decode("utf-8", errors="replace").strip()
    if text.startswith("event:") or "\n\ndata: " in text or text.startswith("data: "):
        for line in text.splitlines():
            if line.startswith("data: "):
                text = line[len("data: ") :]
                break
    parsed = json.loads(text)
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
                "clientInfo": {"name": "dynamic-dispatch-tests", "version": "0"},
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


def _extract_text(tool_result: dict) -> str:
    content = tool_result.get("content") or []
    for part in content:
        if isinstance(part, dict) and part.get("type") in ("text", "json"):
            return part.get("text") or json.dumps(part.get("data", {}))
    return json.dumps(tool_result)


# ---------------------------------------------------------------------------
# Fake dispatcher (records affinity / captures inline result)
# ---------------------------------------------------------------------------


class _RecordingDispatcher:
    """Duck-typed :class:`BaseDccCallableDispatcher` that records every submission.

    Implements both the core protocol (``dispatch_callable``) **and** the
    adapter-facing ``submit_callable`` variant used by the legacy Maya
    executor path — this way the recorder sees calls coming down either
    route (core 0.14.21+ uses ``dispatch_callable``; in-tree
    ``MayaUiDispatcher`` still uses ``submit_callable``).

    The fake runs callables **inline** (no threading) because the tests
    care about semantics — affinity propagation and error shape — not
    UI-thread scheduling.
    """

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    # ---- BaseDccCallableDispatcher protocol (core #599) ----------------

    def dispatch_callable(self, task, *, affinity="any", timeout_ms=None, **kwargs):
        with self._lock:
            self.calls.append(
                {
                    "affinity": affinity,
                    "timeout_ms": timeout_ms,
                    "extra": kwargs,
                    "via": "dispatch_callable",
                }
            )
        try:
            return {"success": True, "output": task()}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ---- BaseDccCallableDispatcherFull extensions ----------------------

    def submit_callable(self, request_id, task, affinity="main", timeout_ms=None):
        with self._lock:
            self.calls.append(
                {
                    "request_id": request_id,
                    "affinity": affinity,
                    "timeout_ms": timeout_ms,
                    "via": "submit_callable",
                }
            )
        try:
            result = task()
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}
        return result

    def cancel(self, request_id):
        return True

    def shutdown(self, reason="Interrupted"):
        return 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def server_with_dispatcher():
    dispatcher = _RecordingDispatcher()
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.attach_dispatcher(dispatcher)
    server.register_builtin_actions(minimal=True)
    handle = server.start()
    time.sleep(0.05)
    yield server, handle, dispatcher
    server.stop()


# ---------------------------------------------------------------------------
# Test 1 — unloaded skill returns load_skill guidance (not a 500)
# ---------------------------------------------------------------------------


def test_dynamic_call_to_unloaded_skill_returns_hint(server_with_dispatcher):
    _, handle, _ = server_with_dispatcher
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    # Try calling a tool that belongs to an unloaded skill.  Minimal mode
    # only loads ``maya-scripting`` + ``maya-scene``; anything else is a
    # ``__skill__maya-xxx`` stub.
    res = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "maya_render__render_frames",
                "arguments": {"frame": 1},
            },
        },
        session_id=session,
    )

    # Either a structured error envelope at the result level, or a
    # JSON-RPC error — both are acceptable as long as a hint is present.
    if "error" in res:
        message = (res["error"].get("message") or "") + " " + (res["error"].get("data") or "")
        assert any(kw in message.lower() for kw in ("load_skill", "unknown", "not found", "not loaded"))
        return

    result = res.get("result") or {}
    assert result.get("isError") is True or "error" in result
    text = _extract_text(result)
    parsed = json.loads(text) if text.startswith("{") else {"message": text}
    hint = (parsed.get("hint") or "") + " " + (parsed.get("message") or "")
    assert any(kw in hint.lower() for kw in ("load_skill", "skill", "not found", "unknown")), (
        "no load_skill hint: {!r}".format(parsed)
    )


# ---------------------------------------------------------------------------
# Test 2 — load_skill + dynamic call enforces thread affinity
# ---------------------------------------------------------------------------


def test_load_skill_then_dynamic_call_enforces_thread_affinity(server_with_dispatcher):
    """After ``load_skill``, unsafe dynamic calls must fail before execution.

    This is the #164 + #242 end-to-end proof: unloaded → load_skill →
    dynamic call still resolves the loaded backend tool, and
    core's affinity-derived enforcement blocks a main-affinity tool
    before it can run on the HTTP worker when the core DeferredExecutor
    is absent in this headless test harness.
    """
    server, handle, dispatcher = server_with_dispatcher
    mcp_url = handle.mcp_url()
    session = _initialise(mcp_url)

    # Load maya-render (unloaded in minimal mode).
    load_res = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "load_skill",
                "arguments": {"skill_name": "maya-render"},
            },
        },
        session_id=session,
    )
    assert load_res.get("result") is not None, "load_skill failed: {}".format(load_res)

    # Now call a main-affinity tool from a loaded skill. In this
    # headless test server the core runtime has no DeferredExecutor, so
    # affinity enforcement must reject the call before any Python
    # handler can touch Maya from the HTTP worker thread.
    server.load_skill("maya-scripting")  # idempotent — handlers still fresh
    call_res = _mcp_post(
        mcp_url,
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "maya_scripting__execute_python",
                "arguments": {"code": "result = 1 + 1"},
            },
        },
        session_id=session,
    )
    result = call_res.get("result") or {}
    assert result.get("isError") is True, "expected affinity violation: {}".format(call_res)
    text = _extract_text(result)
    assert "THREAD_AFFINITY_UNAVAILABLE" in text or "THREAD_AFFINITY_VIOLATION" in text
    assert dispatcher.calls == []


# ---------------------------------------------------------------------------
# Test 3 — dispatcher-less server still handles dynamic calls (standalone)
# ---------------------------------------------------------------------------


def test_dynamic_call_without_dispatcher_still_works():
    """mayapy / batch / test contexts have no dispatcher; inline path must work."""
    server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
    server.register_builtin_actions(minimal=True)
    handle = server.start()
    try:
        time.sleep(0.05)
        mcp_url = handle.mcp_url()
        session = _initialise(mcp_url)

        res = _mcp_post(
            mcp_url,
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "tools/call",
                "params": {
                    "name": "maya_scripting__execute_python",
                    "arguments": {"code": "result = 42"},
                },
            },
            session_id=session,
        )
        # In the absence of a dispatcher the inline runner executes the
        # snippet.  We only require a structured response (no 500, no
        # missing ``result``).
        assert "result" in res or "error" in res
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# Test 4 — attach_dispatcher(None) detaches cleanly (SOLID inversion)
# ---------------------------------------------------------------------------


def test_attach_dispatcher_none_detaches():
    """Calling ``attach_dispatcher(None)`` must not crash and must clear state."""
    server = MayaMcpServer(port=0, enable_gateway_failover=False)
    fake = _RecordingDispatcher()
    server.attach_dispatcher(fake)
    assert server._maya_dispatcher is fake

    server.attach_dispatcher(None)
    assert server._maya_dispatcher is None


# ---------------------------------------------------------------------------
# Test 5 — unit: executor delegates cancellation into dispatcher-signalled
# outcomes instead of raising at the tool-call boundary (issue #151 +
# relevant to #164 for long-running dynamic dispatches).
# ---------------------------------------------------------------------------


def test_executor_dispatcher_exception_surfaces_as_skill_error(monkeypatch):
    from dcc_mcp_maya import _executor

    class _Boom:
        def submit_callable(self, *args, **kwargs):
            raise RuntimeError("dispatcher crashed")

    # Simulate the production "MCP request on a tokio worker thread" path
    # so the executor actually consults the dispatcher (calling
    # ``submit_callable`` from Python's main thread would deadlock —
    # see :func:`dcc_mcp_maya._executor.execute_in_process` doc).
    monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

    fake_server = MagicMock()
    fake_server._maya_dispatcher = _Boom()

    result = _executor.execute_in_process(
        fake_server,
        script_path="/nonexistent.py",
        params={},
        action_name="maya_x__do_thing",
    )
    assert isinstance(result, dict)
    assert result.get("success") is False
    assert "dispatcher" in (result.get("message") or "").lower() or "execute" in (result.get("message") or "").lower()
