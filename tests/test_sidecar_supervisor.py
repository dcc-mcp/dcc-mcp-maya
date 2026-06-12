"""Unit tests for sidecar subprocess supervision."""

from __future__ import annotations

import sys
from pathlib import Path

from dcc_mcp_maya.sidecar import _supervisor
from dcc_mcp_maya.sidecar._supervisor import start_sidecar


class _FakeProc:
    pid = 2468

    def poll(self):
        return None


def _flag_value(cmd, flag):
    index = cmd.index(flag)
    return cmd[index + 1]


def test_start_sidecar_forwards_identity_flags(monkeypatch):
    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = dict(kwargs)
        return _FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "9765")

    handle = start_sidecar(
        maya_pid=1234,
        binary_override=Path("dcc-mcp-server"),
        qt_port_override=45555,
        instance_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        display_name="Maya 2025 pid 1234",
        adapter_version="0.0.0-test",
        gateway_name="dcc-mcp-gateway@workstation-01",
        start_qt_server_fn=lambda port: {
            "host": "127.0.0.1",
            "port": port,
            "qt_binding": "fake-test-stub",
        },
    )

    assert handle.host_rpc_uri == "qtserver://127.0.0.1:45555"
    assert captured["cmd"] == handle.command
    assert captured["cmd"][:2] == ["dcc-mcp-server", "sidecar"]
    assert _flag_value(captured["cmd"], "--dcc") == "maya"
    assert _flag_value(captured["cmd"], "--host-rpc") == "qtserver://127.0.0.1:45555"
    assert _flag_value(captured["cmd"], "--watch-pid") == "1234"
    assert _flag_value(captured["cmd"], "--instance-id") == "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    assert _flag_value(captured["cmd"], "--display-name") == "Maya 2025 pid 1234"
    assert _flag_value(captured["cmd"], "--adapter-version") == "0.0.0-test"
    assert _flag_value(captured["cmd"], "--gateway-name") == "dcc-mcp-gateway@workstation-01"
    assert _flag_value(captured["cmd"], "--gateway-port") == "9765"
    assert _flag_value(captured["cmd"], "--gateway-remote-host") == "0.0.0.0"
    assert _flag_value(captured["cmd"], "--gateway-remote-port") == "59765"
    assert _flag_value(captured["cmd"], "--registry-dir")
    assert captured["kwargs"]["env"]["DCC_MCP_REGISTRY_DIR"] == _flag_value(captured["cmd"], "--registry-dir")
    assert captured["kwargs"]["env"]["DCC_MCP_GATEWAY_PORT"] == "9765"
    assert captured["kwargs"]["env"]["DCC_MCP_GATEWAY_REMOTE_HOST"] == "0.0.0.0"
    assert captured["kwargs"]["env"]["DCC_MCP_GATEWAY_REMOTE_PORT"] == "59765"
    assert handle.launch_contract["role"] == "per-dcc-sidecar"
    assert handle.launch_contract["recommended_next_action"]


def test_start_sidecar_omits_invalid_instance_id(monkeypatch):
    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = dict(kwargs)
        return _FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)

    handle = start_sidecar(
        maya_pid=1234,
        binary_override=Path("dcc-mcp-server"),
        qt_port_override=45555,
        instance_id="unknown",
        start_qt_server_fn=lambda port: {
            "host": "127.0.0.1",
            "port": port,
            "qt_binding": "fake-test-stub",
        },
    )

    assert "--instance-id" not in captured["cmd"]
    assert handle.launch_contract["readiness_selector"]["instance_id"] is None


def test_start_sidecar_captures_stdio_to_registry_logs(monkeypatch, tmp_path):
    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = dict(kwargs)
        return _FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    registry_dir = tmp_path / "registry"

    handle = start_sidecar(
        maya_pid=1234,
        binary_override=Path("dcc-mcp-server"),
        qt_port_override=45555,
        registry_dir=registry_dir,
        start_qt_server_fn=lambda port: {
            "host": "127.0.0.1",
            "port": port,
            "qt_binding": "fake-test-stub",
        },
    )

    stdout_path = Path(captured["kwargs"]["stdout"].name)
    stderr_path = Path(captured["kwargs"]["stderr"].name)
    assert stdout_path.parent == registry_dir / "logs"
    assert stderr_path.parent == registry_dir / "logs"
    assert stdout_path.name.startswith("dcc-mcp-sidecar-1234-")
    assert stderr_path.name.startswith("dcc-mcp-sidecar-1234-")
    assert handle.stdout_path == stdout_path
    assert handle.stderr_path == stderr_path


def test_start_sidecar_honors_extra_env_gateway_port_zero(monkeypatch):
    captured = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = dict(kwargs)
        return _FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "9765")

    start_sidecar(
        maya_pid=1234,
        binary_override=Path("dcc-mcp-server"),
        qt_port_override=45555,
        start_qt_server_fn=lambda port: {
            "host": "127.0.0.1",
            "port": port,
            "qt_binding": "fake-test-stub",
        },
        extra_env={"DCC_MCP_GATEWAY_PORT": "0"},
    )

    assert _flag_value(captured["cmd"], "--gateway-port") == "0"
    assert captured["kwargs"]["env"]["DCC_MCP_GATEWAY_PORT"] == "0"


def test_start_qt_server_imports_core_dispatcher(monkeypatch):
    captured = {}

    def fake_start_qt_server(**kwargs):
        captured.update(kwargs)
        return {
            "host": "127.0.0.1",
            "port": 45555,
            "qt_binding": "fake-core",
        }

    monkeypatch.setattr("dcc_mcp_core.qt_dispatcher.start_qt_server", fake_start_qt_server)

    info = _supervisor._start_qt_server(0, start_qt_server_fn=None)

    assert info["port"] == 45555
    assert captured["port"] == 0
    current_dispatcher = sys.modules["dcc_mcp_maya.sidecar._dispatcher"]
    assert captured["dispatch_handler"] is current_dispatcher.dispatch_payload
