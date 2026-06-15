"""Unit tests for sidecar subprocess supervision."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

import pytest

from dcc_mcp_maya.sidecar import _supervisor
from dcc_mcp_maya.sidecar._supervisor import start_sidecar


class _FakeProc:
    pid = 2468

    def poll(self):
        return None


def _flag_value(cmd, flag):
    index = cmd.index(flag)
    return cmd[index + 1]


@pytest.fixture(autouse=True)
def _fake_core_sidecar_command(monkeypatch):
    def fake_build_sidecar_command(**kwargs):
        registry_dir = Path(kwargs.get("registry_dir") or Path.cwd() / ".test-registry").resolve()
        instance_id = kwargs.get("instance_id")
        normalized_instance_id = None
        if instance_id:
            try:
                normalized_instance_id = str(UUID(str(instance_id)))
            except ValueError:
                normalized_instance_id = None
        gateway_port = str(kwargs.get("gateway_port") if kwargs.get("gateway_port") is not None else 9765)
        command = [
            str(kwargs["server_bin"]),
            "sidecar",
            "--dcc",
            kwargs["dcc_type"],
            "--host-rpc",
            kwargs["host_rpc"],
            "--watch-pid",
            str(kwargs["watch_pid"]),
            "--registry-dir",
            str(registry_dir),
            "--gateway-port",
            gateway_port,
        ]
        for flag, key in (
            ("--instance-id", "instance_id"),
            ("--display-name", "display_name"),
            ("--adapter-version", "adapter_version"),
            ("--discovery-mcp-url", "discovery_mcp_url"),
            ("--gateway-name", "gateway_name"),
            ("--gateway-remote-host", "gateway_remote_host"),
        ):
            value = normalized_instance_id if key == "instance_id" else kwargs.get(key)
            if value:
                command.extend([flag, str(value)])
        if kwargs.get("gateway_remote_port") is not None:
            command.extend(["--gateway-remote-port", str(kwargs["gateway_remote_port"])])
        command.extend(str(arg) for arg in kwargs.get("extra_args") or [])
        return {
            "success": True,
            "role": "per-dcc-sidecar",
            "registry_dir": str(registry_dir),
            "command": command,
            "environment": {
                "set": {
                    "DCC_MCP_REGISTRY_DIR": str(registry_dir),
                    "DCC_MCP_GATEWAY_PORT": gateway_port,
                }
            },
            "readiness_selector": {
                "dcc_type": kwargs["dcc_type"],
                "instance_id": normalized_instance_id,
                "host_rpc": kwargs["host_rpc"],
            },
            "recommended_next_action": "wait for readiness",
        }

    import dcc_mcp_core.install_lifecycle as lifecycle

    monkeypatch.setattr(lifecycle, "build_sidecar_command", fake_build_sidecar_command)


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
        discovery_mcp_url="http://127.0.0.1:8765/mcp",
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
    assert _flag_value(captured["cmd"], "--discovery-mcp-url") == "http://127.0.0.1:8765/mcp"
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


def test_start_sidecar_falls_back_when_core_helper_lacks_discovery_mcp_url(monkeypatch):
    import dcc_mcp_core.install_lifecycle as lifecycle

    captured = {"calls": []}

    def fake_build_sidecar_command(**kwargs):
        captured["calls"].append(dict(kwargs))
        if "discovery_mcp_url" in kwargs:
            raise TypeError("build_sidecar_command() got an unexpected keyword argument 'discovery_mcp_url'")
        registry_dir = Path.cwd() / ".test-registry"
        command = [
            str(kwargs["server_bin"]),
            "sidecar",
            "--dcc",
            kwargs["dcc_type"],
            "--host-rpc",
            kwargs["host_rpc"],
            "--watch-pid",
            str(kwargs["watch_pid"]),
            "--registry-dir",
            str(registry_dir),
            "--gateway-port",
            str(kwargs["gateway_port"]),
        ]
        return {
            "success": True,
            "role": "per-dcc-sidecar",
            "registry_dir": str(registry_dir),
            "command": command,
            "environment": {"set": {"DCC_MCP_REGISTRY_DIR": str(registry_dir)}},
            "readiness_selector": {
                "dcc_type": kwargs["dcc_type"],
                "instance_id": None,
                "host_rpc": kwargs["host_rpc"],
            },
            "recommended_next_action": "wait for readiness",
        }

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = dict(kwargs)
        return _FakeProc()

    monkeypatch.setattr(lifecycle, "build_sidecar_command", fake_build_sidecar_command)
    monkeypatch.setattr("subprocess.Popen", fake_popen)

    handle = start_sidecar(
        maya_pid=1234,
        binary_override=Path("dcc-mcp-server"),
        qt_port_override=45555,
        discovery_mcp_url="http://127.0.0.1:8765/mcp",
        start_qt_server_fn=lambda port: {
            "host": "127.0.0.1",
            "port": port,
            "qt_binding": "fake-test-stub",
        },
    )

    assert len(captured["calls"]) == 2
    assert "discovery_mcp_url" in captured["calls"][0]
    assert "discovery_mcp_url" not in captured["calls"][1]
    assert "--discovery-mcp-url" not in captured["cmd"]
    assert handle.launch_contract["role"] == "per-dcc-sidecar"


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
