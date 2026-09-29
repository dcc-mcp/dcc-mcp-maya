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
    # ``_apply_default_env`` uses ``os.environ.setdefault``; pre-seeding the two
    # ports keeps the deferred callback from leaking them into later tests,
    # which would make port-resolution assertions order-dependent.
    monkeypatch.setenv("DCC_MCP_MAYA_PORT", "0")
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "9765")
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


def _stub_cmds_full(*, load_marks_loaded=True, plugin_loaded=False):
    """``maya.cmds`` stub that also models ``pluginInfo`` / ``loadPlugin``.

    ``load_marks_loaded=False`` simulates a host where the load returns
    cleanly but the plug-in never registers — the silent no-op that started
    this investigation.
    """
    scheduled = []
    warnings = []
    script_jobs = []
    display_warnings = []
    state = {"loaded": plugin_loaded, "load_calls": 0}
    cmds_module = ModuleType("maya.cmds")

    def eval_deferred(callback, **kwargs):
        scheduled.append((callback, kwargs))

    def warning(message):
        warnings.append(message)

    def script_job(**kwargs):
        script_jobs.append(kwargs)
        return len(script_jobs)

    def plugin_info(*_args, **_kwargs):
        return state["loaded"]

    def load_plugin(*_args, **_kwargs):
        state["load_calls"] += 1
        if load_marks_loaded:
            state["loaded"] = True

    cmds_module.evalDeferred = eval_deferred
    cmds_module.warning = warning
    cmds_module.scriptJob = script_job
    cmds_module.pluginInfo = plugin_info
    cmds_module.loadPlugin = load_plugin
    cmds_module._scheduled = scheduled
    cmds_module._warnings = warnings
    cmds_module._script_jobs = script_jobs
    cmds_module._display_warnings = display_warnings
    cmds_module._state = state
    return cmds_module


def _stub_openmaya(display_warnings):
    om_module = ModuleType("maya.api.OpenMaya")
    mglobal = ModuleType("maya.api.OpenMaya.MGlobal")
    mglobal.displayWarning = lambda message: display_warnings.append(message)
    mglobal.displayError = lambda message: display_warnings.append(message)
    om_module.MGlobal = mglobal
    return om_module


def _install_adapter_stub(monkeypatch, *, load_side_effect=None):
    """Inject a fake ``dcc_mcp_maya.install`` so only the load phase varies."""
    calls = []
    install_module = ModuleType("dcc_mcp_maya.install")

    def bootstrap_user_setup(defer=True):
        calls.append({"defer": defer})
        if load_side_effect is not None:
            raise load_side_effect

    install_module.bootstrap_user_setup = bootstrap_user_setup
    package = ModuleType("dcc_mcp_maya")
    package.__path__ = []  # mark as a package so submodule imports resolve
    package.install = install_module
    monkeypatch.setitem(sys.modules, "dcc_mcp_maya", package)
    monkeypatch.setitem(sys.modules, "dcc_mcp_maya.install", install_module)
    return calls


def test_failure_is_mirrored_to_the_maya_status_line(monkeypatch, tmp_path) -> None:
    """MGlobal reaches the status line even when no Script Editor is open."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full()
    om_module = _stub_openmaya(cmds_module._display_warnings)
    api_module = ModuleType("maya.api")
    api_module.OpenMaya = om_module
    monkeypatch.setitem(sys.modules, "maya.api", api_module)
    monkeypatch.setitem(sys.modules, "maya.api.OpenMaya", om_module)

    module = _exec_user_setup(monkeypatch, cmds_module)

    def boom() -> None:
        raise OSError("status line check")

    monkeypatch.setattr(module, "_apply_default_env", boom)
    module._load_dcc_mcp_maya()

    assert cmds_module._display_warnings
    assert "status line check" in cmds_module._display_warnings[0]
    assert [record["stage"] for record in _failures(error_dir)] == ["environment"]


def test_silent_noop_load_is_reported(monkeypatch, tmp_path) -> None:
    """A load that returns without registering the plug-in must not look OK."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full(load_marks_loaded=False)
    module = _exec_user_setup(monkeypatch, cmds_module)
    _install_adapter_stub(monkeypatch)

    module._load_dcc_mcp_maya()

    records = _failures(error_dir)
    assert "plugin_verify" in [record["stage"] for record in records]
    assert cmds_module._warnings, "the silent no-op must reach cmds.warning"


def test_watchdog_arms_a_bounded_idle_scriptjob(monkeypatch, tmp_path) -> None:
    _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full()
    _exec_user_setup(monkeypatch, cmds_module)

    assert len(cmds_module._script_jobs) == 1
    event = cmds_module._script_jobs[0]["event"]
    assert event[0] == "idle"
    assert callable(event[1])


def test_watchdog_retries_then_gives_up_visibly(monkeypatch, tmp_path) -> None:
    """Retries are bounded and the give-up is reported, not silent."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full(load_marks_loaded=False)
    module = _exec_user_setup(monkeypatch, cmds_module)
    _install_adapter_stub(monkeypatch)
    callback = cmds_module._script_jobs[0]["event"][1]

    module.WATCHDOG_GRACE_SECS = 0.0
    for _ in range(module.WATCHDOG_MAX_ATTEMPTS + 2):
        callback()

    stages = [record["stage"] for record in _failures(error_dir)]
    assert "watchdog_give_up" in stages
    assert stages.count("watchdog_give_up") == 1, "the watchdog must give up exactly once"
    assert any("give up" in message or "retries" in message for message in cmds_module._warnings)


def test_watchdog_disarms_when_the_plugin_registers(monkeypatch, tmp_path) -> None:
    """A loaded plug-in stops the watchdog (no permanent polling job)."""
    _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full(load_marks_loaded=False)
    _exec_user_setup(monkeypatch, cmds_module)
    callback = cmds_module._script_jobs[0]["event"][1]

    cmds_module._state["loaded"] = True  # plug-in finished loading after arming
    callback()

    assert any("kill" in kwargs for kwargs in cmds_module._script_jobs[1:])
    assert not cmds_module._warnings


def test_watchdog_absent_scriptjob_is_tolerated(monkeypatch, tmp_path) -> None:
    """Hosts without ``cmds.scriptJob`` keep the deferred-only behaviour."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full()
    del cmds_module.scriptJob
    _exec_user_setup(monkeypatch, cmds_module)

    assert [record["stage"] for record in _failures(error_dir)] == []


def test_failure_record_carries_the_exception_traceback(monkeypatch, tmp_path) -> None:
    """The record must describe ``exc``, not whatever was last being handled.

    The watchdog give-up builds its exception outside an ``except`` block, so
    ``traceback.format_exc()`` would have written ``NoneType: None`` there.
    """
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full()
    module = _exec_user_setup(monkeypatch, cmds_module)

    def raises() -> None:
        raise ValueError("raised inside the load")

    monkeypatch.setattr(module, "_apply_default_env", raises)
    module._load_dcc_mcp_maya()

    records = _failures(error_dir)
    assert records[0]["traceback"]
    assert "ValueError" in records[0]["traceback"]
    assert "raised inside the load" in records[0]["traceback"]
    assert "NoneType: None" not in records[0]["traceback"]


def test_failure_record_for_exception_built_outside_except(monkeypatch, tmp_path) -> None:
    """Reporting an exception that was never raised still records its type."""
    error_dir = _isolate_error_dir(monkeypatch, tmp_path)
    cmds_module = _stub_cmds_full()
    module = _exec_user_setup(monkeypatch, cmds_module)

    module._report_failure("watchdog_give_up", RuntimeError("plug-in never registered"))

    records = _failures(error_dir)
    assert records[0]["stage"] == "watchdog_give_up"
    assert records[0]["error"] == "plug-in never registered"
    assert "NoneType: None" not in records[0]["traceback"]
