"""The real HTTP dispatcher must deliver standalone scene work to main."""

import json
import threading
import time
import urllib.request

from dcc_mcp_maya import MayaMcpServer, _executor
from dcc_mcp_maya.dispatcher import MayaStandaloneDispatcher


def test_standalone_http_scene_call_runs_on_main_thread(monkeypatch, tmp_path):
    monkeypatch.setenv("DCC_MCP_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("DCC_MCP_LOG_DIR", str(tmp_path / "logs"))
    executed = []

    def scene_query(path, params):
        executed.append(threading.get_ident())
        assert threading.current_thread() is threading.main_thread()
        return {"success": True, "scene": "<unsaved>"}

    monkeypatch.setattr(_executor, "run_skill_script", scene_query)
    dispatcher = MayaStandaloneDispatcher()
    server = MayaMcpServer(port=0, gateway_port=0, enable_gateway_failover=False, host_dispatcher=dispatcher)
    outcomes = []
    errors = []

    def client():
        try:
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "maya_scene__get_session_info", "arguments": {}}}
            request = urllib.request.Request(handle.mcp_url(), data=json.dumps(payload).encode(), headers={
                "Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
            with urllib.request.urlopen(request, timeout=5) as response:
                outcomes.append(json.loads(response.read()))
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=client, daemon=True)
    try:
        server.register_builtin_actions(minimal=True)
        handle = server.start()
        assert server.readiness_report()["dcc"] is False
        dispatcher.drain_queue(50)
        assert server.readiness_report()["dcc"] is True
        worker.start()
        deadline = time.monotonic() + 6
        while worker.is_alive() and time.monotonic() < deadline:
            dispatcher.drain_queue(8)
            time.sleep(0.001)
        assert not worker.is_alive()
        assert not errors
        assert executed == [threading.main_thread().ident]
        assert outcomes[0]["result"].get("isError", False) is False
        assert outcomes[0]["result"]["structuredContent"]["success"] is True
    finally:
        server.stop()
        if worker.ident is not None:
            worker.join(timeout=6)
