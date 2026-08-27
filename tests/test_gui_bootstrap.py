"""Behavioral coverage for non-interactive Maya GUI bootstrap diagnostics."""

from __future__ import annotations

import json
import sys
import threading
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from dcc_mcp_maya.gui_bootstrap import (
    bootstrap_in_maya,
    build_maya_launch_args,
    launch_maya_gui,
    main,
    probe_gui_readiness,
    record_bootstrap_stage,
)


def test_maya_gui_launch_args_use_one_fixed_lowest_priority_bootstrap() -> None:
    args = build_maya_launch_args("C:/Program Files/Autodesk/Maya2025/bin/maya.exe")

    assert args[:2] == ["C:/Program Files/Autodesk/Maya2025/bin/maya.exe", "-command"]
    assert len(args) == 3
    assert "cmds.evalDeferred" in args[2]
    assert "lowestPriority=True" in args[2]
    assert "dcc_mcp_maya.gui_bootstrap" in args[2]
    assert "bootstrap_in_maya" in args[2]
    assert "-script" not in args


def test_in_maya_bootstrap_resolves_and_loads_the_plugin_without_changing_autoload(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    plugin_dir = tmp_path / "plug-ins"
    plugin_dir.mkdir()
    plugin_path = plugin_dir / "dcc_mcp_maya_plugin.py"
    plugin_path.write_text("# packaged plugin", encoding="utf-8")
    monkeypatch.setenv("DCC_MCP_MAYA_BOOTSTRAP_LOG", str(log_path))
    monkeypatch.setenv("MAYA_PLUG_IN_PATH", str(plugin_dir))

    maya_module = ModuleType("maya")
    cmds_module = ModuleType("maya.cmds")
    cmds_module.pluginInfo = MagicMock(return_value=False)
    cmds_module.loadPlugin = MagicMock(return_value=["dcc_mcp_maya_plugin"])
    maya_module.cmds = cmds_module

    with patch.dict(sys.modules, {"maya": maya_module, "maya.cmds": cmds_module}):
        bootstrap_in_maya()

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [(event["stage"], event["status"]) for event in events] == [
        ("plugin_invoked", "started"),
        ("plugin_resolution", "started"),
        ("plugin_resolution", "succeeded"),
        ("plugin_load", "started"),
        ("plugin_load", "succeeded"),
    ]
    assert events[2]["plugin_path"] == str(plugin_path.resolve())
    cmds_module.loadPlugin.assert_called_once_with(str(plugin_path.resolve()), quiet=True)
    assert all("autoload" not in call.kwargs for call in cmds_module.pluginInfo.call_args_list)


def test_in_maya_bootstrap_records_resolution_failure_before_raising(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    monkeypatch.setenv("DCC_MCP_MAYA_BOOTSTRAP_LOG", str(log_path))
    monkeypatch.setenv("MAYA_PLUG_IN_PATH", str(tmp_path / "missing"))

    with pytest.raises(RuntimeError, match="packaged dcc-mcp Maya plug-in"):
        bootstrap_in_maya()

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [(event["stage"], event["status"]) for event in events] == [
        ("plugin_invoked", "started"),
        ("plugin_resolution", "started"),
        ("plugin_resolution", "failed"),
    ]
    assert events[-1]["error_type"] == "FileNotFoundError"


def test_in_maya_bootstrap_accepts_plugin_manager_autoload_without_reloading(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    plugin_dir = tmp_path / "plug-ins"
    plugin_dir.mkdir()
    (plugin_dir / "dcc_mcp_maya_plugin.py").write_text("# packaged plugin", encoding="utf-8")
    monkeypatch.setenv("DCC_MCP_MAYA_BOOTSTRAP_LOG", str(log_path))
    monkeypatch.setenv("MAYA_PLUG_IN_PATH", str(plugin_dir))

    maya_module = ModuleType("maya")
    cmds_module = ModuleType("maya.cmds")
    cmds_module.pluginInfo = MagicMock(return_value=True)
    cmds_module.loadPlugin = MagicMock()
    maya_module.cmds = cmds_module

    with patch.dict(sys.modules, {"maya": maya_module, "maya.cmds": cmds_module}):
        bootstrap_in_maya()

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert events[-1]["stage"] == "bootstrap_complete"
    assert events[-1]["status"] == "succeeded"
    assert events[-1]["already_loaded"] is True
    cmds_module.loadPlugin.assert_not_called()


def test_plugin_manager_autoload_does_not_mask_an_existing_sidecar_failure(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    plugin_dir = tmp_path / "plug-ins"
    plugin_dir.mkdir()
    (plugin_dir / "dcc_mcp_maya_plugin.py").write_text("# packaged plugin", encoding="utf-8")
    monkeypatch.setenv("DCC_MCP_MAYA_BOOTSTRAP_LOG", str(log_path))
    monkeypatch.setenv("MAYA_PLUG_IN_PATH", str(plugin_dir))
    record_bootstrap_stage(log_path, "sidecar_spawn", "failed", error_type="SidecarSpawnError")

    maya_module = ModuleType("maya")
    cmds_module = ModuleType("maya.cmds")
    cmds_module.pluginInfo = MagicMock(return_value=True)
    cmds_module.loadPlugin = MagicMock()
    maya_module.cmds = cmds_module

    with patch.dict(sys.modules, {"maya": maya_module, "maya.cmds": cmds_module}):
        bootstrap_in_maya()

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert events[-1]["stage"] == "sidecar_spawn"
    assert events[-1]["status"] == "failed"
    assert events[-1]["error_type"] == "SidecarSpawnError"


def test_launch_maya_gui_passes_only_fixed_command_and_waits_for_target_registry(tmp_path, monkeypatch) -> None:
    maya_executable = tmp_path / "maya.exe"
    maya_executable.write_bytes(b"")
    log_path = tmp_path / "bootstrap.jsonl"
    registry_base = tmp_path / "registry-base"
    captured = {}

    def fake_popen(args, *, env):
        captured["args"] = args
        captured["env"] = env
        record_bootstrap_stage(log_path, "plugin_invoked", "started")
        record_bootstrap_stage(log_path, "plugin_load", "succeeded")
        record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")
        registry_base.mkdir(parents=True)
        (registry_base / "services.json").write_text(
            json.dumps([{"instance_id": "maya-gui", "dcc_type": "maya", "pid": 4125}]),
            encoding="utf-8",
        )
        return SimpleNamespace(pid=4125)

    monkeypatch.setattr("dcc_mcp_maya.gui_bootstrap.subprocess.Popen", fake_popen)

    result = launch_maya_gui(
        maya_executable=maya_executable,
        log_path=log_path,
        registry_base=registry_base,
        timeout_secs=0.1,
    )

    assert result["ready"] is True
    assert result["maya_pid"] == 4125
    assert captured["args"] == build_maya_launch_args(maya_executable)
    assert captured["env"]["DCC_MCP_MAYA_BOOTSTRAP_LOG"] == str(log_path.resolve())
    assert captured["env"]["DCC_MCP_REGISTRY_DIR"] == str(registry_base.resolve())


def test_cli_prints_one_json_diagnosis_and_uses_stable_not_ready_exit(monkeypatch, capsys) -> None:
    monkeypatch.setitem(
        main.__globals__,
        "launch_maya_gui",
        lambda **_kwargs: {
            "ready": False,
            "failure_reason": "plugin_not_invoked",
            "last_stage": None,
            "next_action": {"action": "retry_gui_launch"},
            "maya_pid": 4125,
        },
    )

    exit_code = main(["launch", "--maya-executable", "maya.exe", "--timeout", "0"])

    assert exit_code == 10
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["ready"] is False
    assert payload["failure_reason"] == "plugin_not_invoked"


def test_cli_probe_without_explicit_registry_dir_uses_core_default(tmp_path, monkeypatch, capsys) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    registry_dir = tmp_path / "dcc-mcp-registry"
    registry_dir.mkdir()
    monkeypatch.setenv("DCC_MCP_REGISTRY_DIR", str(tmp_path))
    record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")
    (registry_dir / "services.json").write_text(
        json.dumps([{"instance_id": "maya-default", "dcc_type": "maya", "host_pid": 4125}]),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "probe",
            "--maya-pid",
            "4125",
            "--log-path",
            str(log_path),
            "--timeout",
            "0",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready"] is True
    assert payload["instance"]["instance_id"] == "maya-default"


def test_probe_reports_plugin_not_invoked_when_maya_never_writes_a_stage(tmp_path) -> None:
    result = probe_gui_readiness(
        log_path=tmp_path / "bootstrap.jsonl",
        registry_dir=tmp_path / "registry",
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "plugin_not_invoked"
    assert result["last_stage"] is None
    assert result["next_action"] == {
        "action": "retry_gui_launch",
        "command": "python -m dcc_mcp_maya.gui_bootstrap launch",
    }


def test_probe_reports_plugin_load_failed_with_the_last_deterministic_stage(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    record_bootstrap_stage(log_path, "plugin_invoked", "started")
    record_bootstrap_stage(log_path, "plugin_resolution", "succeeded", plugin_name="dcc_mcp_maya_plugin")
    record_bootstrap_stage(log_path, "plugin_load", "failed", error_type="RuntimeError")

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=tmp_path / "registry",
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "plugin_load_failed"
    assert result["last_stage"] == {
        "stage": "plugin_load",
        "status": "failed",
        "error_type": "RuntimeError",
    }
    assert result["next_action"] == {
        "action": "inspect_bootstrap_log",
        "stage": "plugin_load",
    }


def test_probe_reports_sidecar_failed_after_plugin_startup(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    record_bootstrap_stage(log_path, "plugin_invoked", "started")
    record_bootstrap_stage(log_path, "plugin_load", "succeeded")
    record_bootstrap_stage(log_path, "registry_registration", "succeeded")
    record_bootstrap_stage(log_path, "sidecar_spawn", "failed", error_type="SidecarSpawnError")

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=tmp_path / "registry",
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "sidecar_failed"
    assert result["last_stage"]["stage"] == "sidecar_spawn"
    assert result["next_action"] == {
        "action": "inspect_sidecar_logs",
        "stage": "sidecar_spawn",
    }


def test_probe_reports_registry_registration_failed_after_bootstrap_completes(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    record_bootstrap_stage(log_path, "plugin_invoked", "started")
    record_bootstrap_stage(log_path, "plugin_load", "succeeded")
    record_bootstrap_stage(log_path, "sidecar_spawn", "succeeded")
    record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=tmp_path / "registry",
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "registry_registration_failed"
    assert result["last_stage"]["stage"] == "bootstrap_complete"
    assert result["next_action"] == {
        "action": "inspect_registry",
        "dcc_type": "maya",
        "maya_pid": 4125,
    }


def test_probe_reports_explicit_registry_write_failure(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    record_bootstrap_stage(log_path, "plugin_load", "succeeded")
    record_bootstrap_stage(log_path, "adapter_import", "succeeded")
    record_bootstrap_stage(log_path, "registry_registration", "failed", error_type="OSError")

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=tmp_path / "registry",
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "registry_registration_failed"
    assert result["last_stage"]["stage"] == "registry_registration"
    assert result["next_action"] == {
        "action": "inspect_registry",
        "dcc_type": "maya",
        "maya_pid": 4125,
    }


def test_probe_reports_ready_only_for_the_launched_maya_registry_row(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    record_bootstrap_stage(log_path, "plugin_invoked", "started")
    record_bootstrap_stage(log_path, "plugin_load", "succeeded")
    record_bootstrap_stage(log_path, "sidecar_spawn", "succeeded")
    record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")
    (registry_dir / "services.json").write_text(
        json.dumps(
            [
                {"instance_id": "stale", "dcc_type": "maya", "pid": 9000},
                {
                    "instance_id": "maya-4125",
                    "dcc_type": "maya",
                    "pid": 5000,
                    "host_pid": 4125,
                    "metadata": {"mcp_url": "http://127.0.0.1:49152/mcp"},
                },
            ]
        ),
        encoding="utf-8",
    )

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=registry_dir,
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is True
    assert result["failure_reason"] is None
    assert result["instance"] == {
        "instance_id": "maya-4125",
        "dcc_type": "maya",
        "pid": 5000,
        "host_pid": 4125,
        "mcp_url": "http://127.0.0.1:49152/mcp",
    }
    assert result["next_action"] == {"action": "use_registered_instance", "instance_id": "maya-4125"}


def test_probe_rejects_a_registry_row_for_a_different_maya_pid(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")
    (registry_dir / "services.json").write_text(
        json.dumps([{"instance_id": "other-maya", "dcc_type": "maya", "host_pid": 9000}]),
        encoding="utf-8",
    )

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=registry_dir,
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "registry_registration_failed"
    assert result["next_action"]["maya_pid"] == 4125


def test_probe_ignores_malformed_registry_rows_instead_of_crashing(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")
    (registry_dir / "services.json").write_text(
        json.dumps(
            [
                {"dcc_type": None, "metadata": ["not", "a", "mapping"]},
                {"dcc_type": "maya", "pid": [4125]},
            ]
        ),
        encoding="utf-8",
    )

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=registry_dir,
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "registry_registration_failed"


def test_probe_treats_invalid_registry_json_as_not_registered(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")
    (registry_dir / "services.json").write_text("{not-json", encoding="utf-8")

    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=registry_dir,
        maya_pid=4125,
        timeout_secs=0,
    )

    assert result["ready"] is False
    assert result["failure_reason"] == "registry_registration_failed"


def test_probe_rejects_non_finite_timeout(tmp_path) -> None:
    with pytest.raises(ValueError, match="timeout_secs must be finite"):
        probe_gui_readiness(
            log_path=tmp_path / "bootstrap.jsonl",
            registry_dir=tmp_path / "registry",
            maya_pid=4125,
            timeout_secs=float("nan"),
        )


def test_probe_waits_only_until_the_target_registry_row_becomes_ready(tmp_path) -> None:
    log_path = tmp_path / "bootstrap.jsonl"
    registry_dir = tmp_path / "registry"

    def publish_bootstrap_result() -> None:
        time.sleep(0.03)
        registry_dir.mkdir()
        record_bootstrap_stage(log_path, "plugin_invoked", "started")
        record_bootstrap_stage(log_path, "plugin_load", "succeeded")
        record_bootstrap_stage(log_path, "bootstrap_complete", "succeeded")
        (registry_dir / "services.json").write_text(
            json.dumps([{"instance_id": "maya-ready", "dcc_type": "maya", "pid": 4125}]),
            encoding="utf-8",
        )

    publisher = threading.Thread(target=publish_bootstrap_result)
    publisher.start()
    started = time.monotonic()
    result = probe_gui_readiness(
        log_path=log_path,
        registry_dir=registry_dir,
        maya_pid=4125,
        timeout_secs=0.5,
        poll_interval_secs=0.005,
    )
    elapsed = time.monotonic() - started
    publisher.join(timeout=1)

    assert result["ready"] is True
    assert result["instance"]["instance_id"] == "maya-ready"
    assert elapsed < 0.5
