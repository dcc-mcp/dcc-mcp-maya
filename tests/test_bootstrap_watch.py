"""Coverage for the userSetup bootstrap hang watchdog (started/finished markers).

A bootstrap that *hangs* raises nothing, so ``_report_failure`` never fires and
the operator sees an empty receipts directory. The watchdog makes the pending
state observable: a ``started`` marker that is never retired and outlives the
threshold means the load was attempted and never returned.

The marker is deliberately **run-scoped, not attempt-scoped**. After PR #550
``_load_dcc_mcp_maya`` runs again on every idle-watchdog retry, so a marker per
attempt would let attempt N's exit hide attempt N+1's hang.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from types import ModuleType

from dcc_mcp_maya import _bootstrap_watch as watch

USER_SETUP_PATH = Path(__file__).resolve().parents[1] / "maya" / "userSetup.py"


def _isolate(monkeypatch, tmp_path):
    """Point every bootstrap receipt at ``tmp_path`` and pin the leaked env.

    ``userSetup._apply_default_env`` calls ``os.environ.setdefault`` for the
    port variables. Pre-seeding them keeps the callback from permanently
    mutating the process environment, which would otherwise make
    ``tests/test_server.py``'s port-resolution assertions order-dependent.
    """
    monkeypatch.setenv(watch.ENV_BOOTSTRAP_ERROR_DIR, str(tmp_path))
    monkeypatch.setenv("DCC_MCP_MAYA_PORT", "0")
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "9765")
    return tmp_path


def _write_marker(tmp_path, run_id, age_secs, hang_reported=False):
    """Drop a pending marker that claims to have started ``age_secs`` ago."""
    pending = tmp_path / watch.PENDING_DIR_NAME
    pending.mkdir(parents=True, exist_ok=True)
    marker = {
        "schema_version": watch.SCHEMA_VERSION,
        "run_id": run_id,
        "stage": watch.BOOTSTRAP_STAGE,
        "status": watch.STATUS_STARTED,
        "timestamp_utc": "2026-09-29T05:04:50.207881+00:00",
        "timestamp_epoch": time.time() - age_secs,
        "pid": 4242,
        "host": "ARTIST-01",
        "hang_reported": hang_reported,
    }
    path = pending / "{}.json".format(run_id)
    path.write_text(json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _records(tmp_path):
    records = []
    for path in sorted(Path(tmp_path).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            records.append(json.loads(line))
    return records


def test_resolve_bootstrap_timeout_defaults_to_sixty(monkeypatch) -> None:
    monkeypatch.delenv(watch.ENV_BOOTSTRAP_TIMEOUT, raising=False)
    assert watch.resolve_bootstrap_timeout_secs() == watch.DEFAULT_BOOTSTRAP_TIMEOUT_SECS
    assert watch.DEFAULT_BOOTSTRAP_TIMEOUT_SECS == 60.0


def test_resolve_bootstrap_timeout_is_configurable(monkeypatch) -> None:
    monkeypatch.setenv(watch.ENV_BOOTSTRAP_TIMEOUT, "5")
    assert watch.resolve_bootstrap_timeout_secs() == 5.0

    monkeypatch.setenv(watch.ENV_BOOTSTRAP_TIMEOUT, "0")
    assert watch.resolve_bootstrap_timeout_secs() is None

    monkeypatch.setenv(watch.ENV_BOOTSTRAP_TIMEOUT, "not-a-number")
    assert watch.resolve_bootstrap_timeout_secs() == watch.DEFAULT_BOOTSTRAP_TIMEOUT_SECS


def test_started_without_finished_is_judged_a_hang(monkeypatch, tmp_path) -> None:
    """Acceptance: started written, finished never written => hang."""
    _isolate(monkeypatch, tmp_path)
    _write_marker(tmp_path, "run-hung", age_secs=120.0)

    reports = watch.detect_bootstrap_hang()

    assert len(reports) == 1
    report = reports[0]
    assert report["hang"] is True
    assert report["run_id"] == "run-hung"
    assert report["stage"] == watch.BOOTSTRAP_STAGE
    assert report["pid"] == 4242
    assert report["host"] == "ARTIST-01"
    assert report["age_secs"] >= 120.0
    assert report["threshold_secs"] == 60.0
    assert report["next_action"] == "inspect_bootstrap_hang"
    assert Path(report["marker_path"]).is_file()


def test_finished_load_leaves_no_pending_marker(monkeypatch, tmp_path) -> None:
    """Acceptance: the normal path must leave no started residue."""
    _isolate(monkeypatch, tmp_path)
    marker = watch.record_bootstrap_started()
    assert marker["status"] == watch.STATUS_STARTED
    assert marker["pid"] and marker["host"] and marker["timestamp_utc"]
    assert Path(marker["marker_path"]).is_file()
    assert watch.read_pending_markers()  # marker is in flight right now

    finished = watch.record_bootstrap_finished(marker)
    assert finished["status"] == watch.STATUS_FINISHED
    assert finished["run_id"] == marker["run_id"]

    assert watch.read_pending_markers() == []
    assert watch.detect_bootstrap_hang() == []

    # ``pending/`` holds in-flight state; the JSONL holds terminal events.
    assert [record["status"] for record in _records(tmp_path)] == [watch.STATUS_FINISHED]


def test_threshold_is_configurable(monkeypatch, tmp_path) -> None:
    """Acceptance: the hang threshold follows DCC_MCP_MAYA_BOOTSTRAP_TIMEOUT."""
    _isolate(monkeypatch, tmp_path)
    _write_marker(tmp_path, "run-slow", age_secs=10.0)

    monkeypatch.setenv(watch.ENV_BOOTSTRAP_TIMEOUT, "5")
    assert len(watch.detect_bootstrap_hang()) == 1

    monkeypatch.setenv(watch.ENV_BOOTSTRAP_TIMEOUT, "300")
    assert watch.detect_bootstrap_hang() == []

    monkeypatch.setenv(watch.ENV_BOOTSTRAP_TIMEOUT, "0")
    assert watch.detect_bootstrap_hang() == []


def test_detection_is_per_run_not_global(monkeypatch, tmp_path) -> None:
    """Two concurrent Maya sessions must not mask each other's hang."""
    _isolate(monkeypatch, tmp_path)
    _write_marker(tmp_path, "run-a", age_secs=300.0)
    _write_marker(tmp_path, "run-b", age_secs=1.0)

    reports = watch.detect_bootstrap_hang()
    assert [report["run_id"] for report in reports] == ["run-a"]

    # The healthy session finishes and retires only its own marker.
    watch.clear_bootstrap_marker({"run_id": "run-b"})
    assert [report["run_id"] for report in watch.detect_bootstrap_hang()] == ["run-a"]


def test_report_bootstrap_hang_writes_retrievable_evidence(monkeypatch, tmp_path) -> None:
    """Acceptance: evidence must be greppable, not just one JSONL line."""
    _isolate(monkeypatch, tmp_path)
    _write_marker(tmp_path, "run-evidence", age_secs=600.0)

    warnings = []
    monkeypatch.setattr(watch, "_warn", warnings.append)

    reports = watch.report_bootstrap_hang()

    assert len(reports) == 1
    assert reports[0]["reported"] is True
    assert len(warnings) == 1
    assert "hang detected" in warnings[0]
    assert "run-evidence" in warnings[0]

    hang_records = [record for record in _records(tmp_path) if record.get("status") == watch.STATUS_HANG_DETECTED]
    assert len(hang_records) == 1
    assert hang_records[0]["run_id"] == "run-evidence"
    assert hang_records[0]["evidence_log"] == str(tmp_path)

    # The marker stays on disk as durable evidence but is flagged as announced,
    # so a permanently wedged Maya does not flood the Script Editor.
    assert json.loads(Path(reports[0]["marker_path"]).read_text(encoding="utf-8"))["hang_reported"] is True

    warnings.clear()
    again = watch.report_bootstrap_hang()
    assert len(again) == 1
    assert again[0]["reported"] is False
    assert warnings == []


def test_report_bootstrap_hang_is_a_no_op_when_healthy(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    warnings = []
    monkeypatch.setattr(watch, "_warn", warnings.append)

    assert watch.report_bootstrap_hang() == []
    assert warnings == []
    assert _records(tmp_path) == []


def test_clear_bootstrap_marker_tolerates_missing_marker(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    assert watch.clear_bootstrap_marker(None) is False
    assert watch.clear_bootstrap_marker({}) is False
    assert watch.clear_bootstrap_marker({"run_id": "never-existed"}) is False


def _exec_user_setup(monkeypatch, cmds_module):
    maya_module = ModuleType("maya")
    maya_module.cmds = cmds_module
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds_module)

    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_user_setup_hang", USER_SETUP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_cmds(*, with_eval_deferred=True, plugin_loaded=True):
    scheduled = []
    warnings = []
    cmds_module = ModuleType("maya.cmds")

    def eval_deferred(callback, **kwargs):
        scheduled.append((callback, kwargs))

    cmds_module.pluginInfo = lambda *_args, **_kwargs: plugin_loaded
    cmds_module.warning = warnings.append
    if with_eval_deferred:
        cmds_module.evalDeferred = eval_deferred
    return cmds_module, scheduled, warnings


def _install_adapter_stub(monkeypatch, side_effect=None):
    """Inject a fake ``dcc_mcp_maya.install`` so no plug-in is really loaded."""
    calls = []
    install_module = ModuleType("dcc_mcp_maya.install")

    def bootstrap_user_setup(defer=True):
        calls.append({"defer": defer})
        if side_effect is not None:
            raise side_effect

    install_module.bootstrap_user_setup = bootstrap_user_setup
    monkeypatch.setitem(sys.modules, "dcc_mcp_maya.install", install_module)
    return calls


def test_marker_is_written_once_per_run_before_the_first_schedule(monkeypatch, tmp_path) -> None:
    """PM condition 1: one marker per run, written before the first schedule.

    The idle watchdog calls ``_load_dcc_mcp_maya`` again on every retry, so a
    marker per attempt would let attempt N's exit mask attempt N+1's hang.
    """
    _isolate(monkeypatch, tmp_path)
    cmds_module, scheduled, _ = _stub_cmds()
    calls = _install_adapter_stub(monkeypatch)

    order = []
    real_started = watch.record_bootstrap_started

    def spy_started(*args, **kwargs):
        order.append("started")
        return real_started(*args, **kwargs)

    monkeypatch.setattr(watch, "record_bootstrap_started", spy_started)
    _exec_user_setup(monkeypatch, cmds_module)

    assert order == ["started"], "the marker must be written before the first schedule"
    assert len(watch.read_pending_markers()) == 1

    # Run the whole legitimate retry chain: the marker must not be rewritten.
    for _ in range(3):
        callback, _ = scheduled[0]
        callback()

    assert order == ["started"], "retries must never rewrite the run marker"
    # ...and the successful load retires it exactly once.
    assert watch.read_pending_markers() == []
    assert [record["status"] for record in _records(tmp_path)] == [watch.STATUS_FINISHED]
    assert len(calls) >= 1


def test_watchdog_give_up_retires_the_marker(monkeypatch, tmp_path) -> None:
    """PM condition 2: a give-up is a reported failure, so it must not linger."""
    _isolate(monkeypatch, tmp_path)
    cmds_module, scheduled, warnings = _stub_cmds(plugin_loaded=False)
    script_jobs = []
    cmds_module.scriptJob = lambda **kwargs: script_jobs.append(kwargs) or len(script_jobs)
    _install_adapter_stub(monkeypatch)
    module = _exec_user_setup(monkeypatch, cmds_module)

    assert len(watch.read_pending_markers()) == 1, "a marker is armed while the run is in flight"

    module.WATCHDOG_GRACE_SECS = 0.0
    callback = script_jobs[0]["event"][1]
    for _ in range(module.WATCHDOG_MAX_ATTEMPTS + 2):
        callback()

    stages = [record["stage"] for record in _records(tmp_path)]
    assert "watchdog_give_up" in stages
    # Retired: a give-up must never be misread as a hang on the next start-up.
    assert watch.read_pending_markers() == []
    assert watch.detect_bootstrap_hang() == []


def test_healthy_retry_chain_is_never_reported_as_a_hang(monkeypatch, tmp_path) -> None:
    """PM condition 3: 60s must strictly exceed the worst-case retry window.

    PR #550 retries up to ``WATCHDOG_MAX_ATTEMPTS`` times spaced by
    ``WATCHDOG_GRACE_SECS``. A slow-but-working session must not be misreported
    as hung, so the default threshold has to clear that whole window.
    """
    _isolate(monkeypatch, tmp_path)
    cmds_module, scheduled, _ = _stub_cmds(plugin_loaded=False)
    script_jobs = []
    cmds_module.scriptJob = lambda **kwargs: script_jobs.append(kwargs) or len(script_jobs)
    _install_adapter_stub(monkeypatch)
    module = _exec_user_setup(monkeypatch, cmds_module)

    worst_case = module.WATCHDOG_WORST_CASE_SECS
    assert module.WATCHDOG_GRACE_SECS * (module.WATCHDOG_MAX_ATTEMPTS + 1) == worst_case
    assert watch.DEFAULT_BOOTSTRAP_TIMEOUT_SECS > worst_case, (
        "the default threshold must strictly exceed the worst-case legitimate retry window"
    )

    # Walk the entire legitimate retry window in small steps and assert that a
    # run still inside it is never judged hung.
    steps = int(worst_case) + 1
    for elapsed in range(steps + 1):
        reports = watch.detect_bootstrap_hang(now=time.time() + elapsed)
        assert reports == [], "elapsed={}s inside the retry window must not be a hang".format(elapsed)

    # Just past the threshold the same stalled run *is* a hang.
    past = watch.DEFAULT_BOOTSTRAP_TIMEOUT_SECS + 1.0
    assert len(watch.detect_bootstrap_hang(now=time.time() + past)) == 1


def test_failed_load_without_a_watchdog_retires_the_marker(monkeypatch, tmp_path) -> None:
    """With no watchdog armed a failed attempt is terminal, not retryable."""
    _isolate(monkeypatch, tmp_path)
    cmds_module, scheduled, _ = _stub_cmds()
    _install_adapter_stub(monkeypatch, side_effect=RuntimeError("loadPlugin exploded"))
    _exec_user_setup(monkeypatch, cmds_module)

    scheduled[0][0]()

    assert watch.read_pending_markers() == []
    assert watch.detect_bootstrap_hang() == []
    stages = [record["stage"] for record in _records(tmp_path)]
    assert stages == ["plugin_load"]


def test_no_marker_outside_a_maya_session(monkeypatch, tmp_path) -> None:
    """Outside Maya nothing can retire a marker, so none may be written."""
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setitem(sys.modules, "maya", None)

    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_user_setup_hang", USER_SETUP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._maya_cmds() is None
    assert watch.read_pending_markers() == []
    assert _records(tmp_path) == []


def test_failed_schedule_does_not_leave_a_marker(monkeypatch, tmp_path) -> None:
    """A load that was never queued must not look like one that never returned."""
    _isolate(monkeypatch, tmp_path)
    cmds_module, scheduled, _ = _stub_cmds(with_eval_deferred=False)
    _exec_user_setup(monkeypatch, cmds_module)

    assert scheduled == []
    assert watch.read_pending_markers() == []
    assert [record["stage"] for record in _records(tmp_path)] == ["schedule"]


def test_user_setup_announces_a_hang_from_the_previous_launch(monkeypatch, tmp_path) -> None:
    """Acceptance: the next start-up must surface the wedged marker."""
    _isolate(monkeypatch, tmp_path)
    _write_marker(tmp_path, "run-yesterday", age_secs=3600.0)

    cmds_module, scheduled, warnings = _stub_cmds()
    _install_adapter_stub(monkeypatch)
    _exec_user_setup(monkeypatch, cmds_module)

    assert len(warnings) == 1
    assert "hang detected" in warnings[0]
    assert "run-yesterday" in warnings[0]
    # Detection runs at import time, so it still fires when the deferred
    # callback never runs -- which is exactly the hang scenario.
    assert len(scheduled) == 1
