"""Real scene reads must survive HTTP worker dispatch in mayapy."""

import threading

import pytest

from dcc_mcp_maya import MayaMcpServer, _executor
from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher

from ._support import _mcp_post, _mcp_post_blocking, cmds

pytestmark = pytest.mark.e2e


def test_repeated_scene_requests_execute_on_maya_main_thread(monkeypatch):
    original = _executor.run_skill_script
    threads = []

    def checked_runner(path, params):
        threads.append(threading.get_ident())
        assert threading.current_thread() is threading.main_thread()
        return original(path, params)

    monkeypatch.setattr(_executor, "run_skill_script", checked_runner)
    dispatcher = MayaStandaloneDispatcher()
    server = MayaMcpServer(port=0, gateway_port=0, enable_gateway_failover=False, host_dispatcher=dispatcher)
    try:
        server.register_builtin_actions(minimal=True)
        handle = server.start()
        assert server.readiness_report()["dcc"] is False
        for ident in range(3):
            code, reply = _mcp_post(
                handle.mcp_url(),
                {
                    "jsonrpc": "2.0",
                    "id": ident,
                    "method": "tools/call",
                    "params": {"name": "maya_scene__get_session_info", "arguments": {}},
                },
            )
            assert code == 200
            result = reply["result"]
            assert not result.get("isError"), result
            data = result["structuredContent"]
            assert data["success"] is True
            assert data["context"]["maya_version"] == cmds.about(version=True)
            assert data["context"]["scene_modified"] == cmds.file(q=True, modified=True)
        assert threads == [threading.main_thread().ident] * 3
        assert server.readiness_report()["dcc"] is True
    finally:
        server.stop()
    assert not server.is_running


def test_serve_headless_scene_request_and_clean_stop(monkeypatch):
    from dcc_mcp_maya.headless import serve_headless

    original = cmds.about
    executed = []
    request_in_flight = threading.Event()
    stop = threading.Event()
    replies = []
    errors = []
    workers = []
    version = cmds.about(version=True)

    def checked_about(*args, **kwargs):
        # Observe Maya itself even if plugin lifecycle tests reimport the adapter.
        if request_in_flight.is_set() and kwargs.get("version"):
            executed.append(threading.get_ident())
            assert threading.current_thread() is threading.main_thread()
        return original(*args, **kwargs)

    monkeypatch.setattr(cmds, "about", checked_about)

    def announce(server):
        def client():
            try:
                request_in_flight.set()
                code, reply = _mcp_post_blocking(
                    server.mcp_url,
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": "maya_scene__get_session_info", "arguments": {}},
                    },
                    10,
                )
                assert code == 200
                replies.append(reply)
            except Exception as exc:
                errors.append(exc)
            finally:
                request_in_flight.clear()
                stop.set()

        worker = threading.Thread(target=client, daemon=True)
        workers.append(worker)
        worker.start()

    serve_headless(port=0, gateway_port=0, stop_event=stop, on_started=announce)
    workers[0].join(timeout=2)
    assert not workers[0].is_alive()
    assert not errors
    assert not replies[0]["result"].get("isError"), replies
    data = replies[0]["result"]["structuredContent"]
    assert data["success"] is True and data["context"]["maya_version"] == version
    assert executed and all(ident == threading.main_thread().ident for ident in executed)
