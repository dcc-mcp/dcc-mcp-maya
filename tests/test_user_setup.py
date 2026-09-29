"""Regression coverage for the bundled Maya GUI bootstrap."""

from __future__ import annotations

import builtins
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

USER_SETUP_PATH = Path(__file__).resolve().parents[1] / "maya" / "userSetup.py"


def _exec_user_setup(monkeypatch, cmds_module, extra_modules=None):
    """Execute ``maya/userSetup.py`` against a stubbed ``maya`` package."""
    maya_module = ModuleType("maya")
    maya_module.cmds = cmds_module
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds_module)
    for name, module in (extra_modules or {}).items():
        monkeypatch.setitem(sys.modules, name, module)
        if name.startswith("maya."):
            setattr(maya_module, name.split(".", 1)[1], module)

    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_user_setup", USER_SETUP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_cmds(*, with_eval_deferred=True, eval_error=None):
    """Build a ``maya.cmds`` stub whose scheduling and warnings are observable."""
    scheduled = []
    warnings = []
    cmds_module = ModuleType("maya.cmds")

    def eval_deferred(callback, **kwargs):
        if eval_error is not None:
            raise eval_error
        scheduled.append((callback, kwargs))

    def warning(message):
        warnings.append(message)

    if with_eval_deferred:
        cmds_module.evalDeferred = eval_deferred
    cmds_module.warning = warning
    return cmds_module, scheduled, warnings


def _failures(error_dir):
    records = []
    for path in sorted(Path(error_dir).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            records.append(json.loads(line))
    return records


def _isolate_error_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR", str(tmp_path))
    return tmp_path


def test_user_setup_uses_maya_lowest_priority_queue(monkeypatch, tmp_path) -> None:
    _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module, scheduled, _ = _stub_cmds()
    module = _exec_user_setup(monkeypatch, cmds_module)

    assert len(scheduled) == 1
    callback, kwargs = scheduled[0]
    assert callback is module._load_dcc_mcp_maya
    assert kwargs == {"lowestPriority": True}


def test_user_setup_schedules_via_cmds_not_maya_utils(monkeypatch, tmp_path) -> None:
    """Scheduling must use ``cmds.evalDeferred``, never ``maya.utils.executeDeferred``.

    ``maya.utils.executeDeferred`` runs on the *idle event loop*: its own
    docstring requires the main thread to become idle before the callback
    runs. During a GUI start-up that idle state may never arrive, which is
    exactly why the adapter silently never loaded. ``cmds.evalDeferred``
    drains as part of Maya's start-up sequence instead.
    """
    _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module, scheduled, _ = _stub_cmds()

    utils_calls = []
    utils_module = ModuleType("maya.utils")
    utils_module.executeDeferred = lambda callback, **kwargs: utils_calls.append((callback, kwargs))

    _exec_user_setup(monkeypatch, cmds_module, {"maya.utils": utils_module})

    assert utils_calls == []
    assert len(scheduled) == 1
    assert scheduled[0][1] == {"lowestPriority": True}


def test_user_setup_reports_missing_eval_deferred(monkeypatch, tmp_path) -> None:
    """A missing scheduler must be reported, not swallowed by ``except ImportError``."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module, scheduled, warnings = _stub_cmds(with_eval_deferred=False)
    _exec_user_setup(monkeypatch, cmds_module)

    assert scheduled == []
    assert warnings and "schedule" in warnings[0]
    records = _failures(error_dir)
    assert [record["stage"] for record in records] == ["schedule"]
    assert records[0]["error_type"] == "RuntimeError"


def test_user_setup_reports_scheduling_error(monkeypatch, tmp_path) -> None:
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module, scheduled, warnings = _stub_cmds(
        eval_error=TypeError("evalDeferred() got an unexpected keyword argument")
    )
    _exec_user_setup(monkeypatch, cmds_module)

    assert scheduled == []
    assert warnings and "schedule" in warnings[0]
    records = _failures(error_dir)
    assert [record["stage"] for record in records] == ["schedule"]
    assert records[0]["error_type"] == "TypeError"


def test_user_setup_reports_environment_failure(monkeypatch, tmp_path) -> None:
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module, scheduled, warnings = _stub_cmds()
    module = _exec_user_setup(monkeypatch, cmds_module)

    def boom() -> None:
        raise OSError("read-only environment")

    monkeypatch.setattr(module, "_apply_default_env", boom)
    callback, _ = scheduled[0]
    callback()

    assert warnings and "environment" in warnings[0]
    records = _failures(error_dir)
    assert [record["stage"] for record in records] == ["environment"]
    assert records[0]["error_type"] == "OSError"
    assert "OSError" in records[0]["traceback"]


def test_user_setup_reports_unimportable_adapter(monkeypatch, tmp_path) -> None:
    """A host that has the plug-in but no adapter package must say so out loud."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module, scheduled, warnings = _stub_cmds()
    _exec_user_setup(monkeypatch, cmds_module)

    monkeypatch.setitem(sys.modules, "dcc_mcp_maya", None)
    callback, _ = scheduled[0]
    callback()

    records = _failures(error_dir)
    assert [record["stage"] for record in records] == ["import"]
    assert issubclass(getattr(builtins, records[0]["error_type"]), ImportError)
    assert warnings[0].startswith("dcc-mcp-maya auto-load failed")


def test_user_setup_is_silent_outside_maya(monkeypatch, tmp_path) -> None:
    """Outside a Maya interpreter the module must stay quiet, not log noise."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    monkeypatch.setitem(sys.modules, "maya", None)

    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_user_setup", USER_SETUP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._maya_cmds() is None
    assert _failures(error_dir) == []
