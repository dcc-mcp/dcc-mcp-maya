"""Unit tests for sidecar subprocess supervision."""

from __future__ import annotations

from pathlib import Path

from dcc_mcp_maya.sidecar._supervisor import start_sidecar


class _FakeProc:
    pid = 2468

    def poll(self):
        return None


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
    assert captured["cmd"] == [
        "dcc-mcp-server",
        "sidecar",
        "--dcc",
        "maya",
        "--host-rpc",
        "qtserver://127.0.0.1:45555",
        "--watch-pid",
        "1234",
        "--instance-id",
        "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        "--display-name",
        "Maya 2025 pid 1234",
        "--adapter-version",
        "0.0.0-test",
        "--gateway-name",
        "dcc-mcp-gateway@workstation-01",
        "--gateway-port",
        "9765",
    ]


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

    assert "--gateway-port" not in captured["cmd"]
    assert captured["kwargs"]["env"]["DCC_MCP_GATEWAY_PORT"] == "0"
