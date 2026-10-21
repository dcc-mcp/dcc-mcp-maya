"""Coverage for the userSetup bootstrap hang watchdog (started/finished markers).

A bootstrap that *hangs* raises nothing, so ``_report_failure`` never fires and
the operator sees an empty receipts directory. The watchdog makes the pending
state observable: a ``started`` marker that is never retired and outlives the
threshold means the load was attempted and never returned.

The marker is deliberately **run-scoped, not attempt-scoped**. After PR #550
``_load_dcc_mcp_maya`` runs again on every watchdog retry, so a marker per
attempt would let attempt N's exit hide attempt N+1's hang.
"""

from __future__ import annotations

import ast as _ast
import contextlib
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


def _install_core_stub(monkeypatch):
    """Pin a core that *can* capture bootstrap errors.

    ``userSetup`` suppresses the local record only when core owns the capture
    path, and core does not own it below 0.19.90 -- which is the version the
    mayapy floor lane installs. Without this pin the dedupe assertion below
    would silently mean different things on different core versions.
    """
    core_module = ModuleType("dcc_mcp_core")
    core_module.__version__ = "0.19.90"

    @contextlib.contextmanager
    def capture_bootstrap_errors(dcc_name, **_kwargs):
        # Records and re-raises in reality; nothing here reaches it.
        yield

    core_module.capture_bootstrap_errors = capture_bootstrap_errors
    monkeypatch.setitem(sys.modules, "dcc_mcp_core", core_module)
    return core_module


def test_marker_is_written_once_per_run_before_the_first_schedule(monkeypatch, tmp_path) -> None:
    """PM condition 1: one marker per run, written before the first schedule.

    The watchdog calls ``_load_dcc_mcp_maya`` again on every retry, so a
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


def test_watchdog_give_up_retires_the_marker(monkeypatch, tmp_path, watchdog_qt) -> None:
    """PM condition 2: a give-up is a reported failure, so it must not linger."""
    _isolate(monkeypatch, tmp_path)
    cmds_module, scheduled, warnings = _stub_cmds(plugin_loaded=False)
    _install_adapter_stub(monkeypatch)
    module = _exec_user_setup(monkeypatch, cmds_module)

    assert len(watch.read_pending_markers()) == 1, "a marker is armed while the run is in flight"

    module.WATCHDOG_GRACE_SECS = 0.0
    callback = watchdog_qt[0].fire
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
    """With no watchdog armed a failed attempt is terminal, not retryable.

    The failure surfaces on ``cmds.warning`` but leaves no local record:
    with a core that owns the capture path, ``plugin_load`` is one of the
    stages core's ``capture_bootstrap_errors`` already persisted, so a second
    record here would be the duplicate this channel was cleaned up to remove.
    """
    _isolate(monkeypatch, tmp_path)
    cmds_module, scheduled, warnings = _stub_cmds()
    _install_core_stub(monkeypatch)
    _install_adapter_stub(monkeypatch, side_effect=RuntimeError("loadPlugin exploded"))
    _exec_user_setup(monkeypatch, cmds_module)

    scheduled[0][0]()

    assert watch.read_pending_markers() == []
    assert watch.detect_bootstrap_hang() == []
    assert warnings and "plugin_load" in warnings[0], "the failure must still reach the Script Editor"
    assert [record for record in _records(tmp_path) if record.get("status") == "failed"] == []


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


def test_watchdog_records_use_lf_line_endings(monkeypatch, tmp_path) -> None:
    """The watchdog shares the JSONL with userSetup, so it must write LF too.

    ``_append_record`` targets the very same ``userSetup-<YYYYMMDD>.jsonl``
    that ``maya/userSetup.py`` appends ``failed`` records to. In the default
    text mode Windows rewrites the trailing ``\n`` to CRLF, which would leave
    one file carrying two line endings -- the userSetup half LF and the
    watchdog half CRLF -- and undo the line-ending guarantee the other half
    of this log was changed to provide.
    """
    _isolate(monkeypatch, tmp_path)
    marker = watch.record_bootstrap_started()
    watch.record_bootstrap_finished(marker)

    payload = watch.bootstrap_log_path().read_bytes()
    assert payload, "the finished event must have been appended"
    assert b"\r\n" not in payload, "Windows text mode would emit CRLF"
    assert payload.endswith(b"\n")


def _fill_watch_log(monkeypatch, tmp_path, *, generations, details=None):
    """Append ``finished`` records until the log has rolled ``generations`` times.

    A real ``finished`` record is ~327 B, so filling one 5 MiB generation from
    genuine launch-sized records takes ~16k appends -- far too slow for a unit
    test, and it would make the suite the thing that needs optimising. The
    records here are still written through the real public path
    (``record_bootstrap_finished`` -> ``_append_record``); only the free-form
    ``filler`` field is enlarged so a handful of writes covers several
    generations. Rotation, the cap check, and the ordering guarantees under
    test are all exercised exactly as they are in production.
    """
    chunk = watch.BOOTSTRAP_ERROR_MAX_BYTES // 4
    for index in range(generations * 4 + 2):
        payload = {"filler": "F" * chunk, "seq": index}
        payload.update(details or {})
        watch.record_bootstrap_finished(None, **payload)


def test_watch_only_writes_stay_bounded_by_the_rotation_cap(monkeypatch, tmp_path) -> None:
    """Acceptance: watch-only growth is capped at MAX_BYTES x (BACKUP_COUNT + 1).

    ``finished`` / ``hang_detected`` records are the *only* writer once a studio
    has fixed whatever was failing, and they accumulate on every healthy launch.
    Before this change ``_append_record`` just appended: the sole rotation path
    lived in ``maya/userSetup.py``'s ``_write_failure_record``, which never runs
    when nothing fails. So the log was bounded only while it was also being
    filled with failures -- unbounded precisely in the healthy period.

    This is proven by appending, not inferred: write well past the cap, then
    assert the directory never holds more than the budget allows and no
    generation exists beyond ``BACKUP_COUNT``.
    """
    _isolate(monkeypatch, tmp_path)
    max_bytes = watch.BOOTSTRAP_ERROR_MAX_BYTES
    backup_count = watch.BOOTSTRAP_ERROR_BACKUP_COUNT

    _fill_watch_log(monkeypatch, tmp_path, generations=backup_count + 2)

    live = watch.bootstrap_log_path()
    assert live.exists()
    # The live file never exceeds a single generation...
    assert live.stat().st_size <= max_bytes, "the live log grew past one generation"

    # ...at most BACKUP_COUNT rotated generations exist...
    for generation in range(1, backup_count + 1):
        rotated = live.with_name("{}.{}".format(live.name, generation))
        assert rotated.exists(), "generation {} should exist after this much appending".format(generation)
        assert rotated.stat().st_size <= max_bytes
    assert not live.with_name("{}.{}".format(live.name, backup_count + 1)).exists()

    # ...so the whole day's directory is bounded at MAX_BYTES x (BACKUP_COUNT + 1).
    budget = max_bytes * (backup_count + 1)
    on_disk = sum(path.stat().st_size for path in Path(tmp_path).glob("userSetup-*"))
    assert on_disk <= budget, "directory holds {} bytes, cap is {}".format(on_disk, budget)


def test_watch_only_growth_is_bounded_without_any_failed_records(monkeypatch, tmp_path) -> None:
    """The bounded-growth assertion must hold with zero ``failed`` records.

    Separate from the byte-budget test above on purpose: that one proves the
    cap, this one proves the *scenario* -- no ``_write_failure_record`` call
    ever happens here, so nothing on the userSetup side can be doing the
    rotating. If this passes, the watch side is genuinely self-bounding.
    """
    _isolate(monkeypatch, tmp_path)
    _fill_watch_log(monkeypatch, tmp_path, generations=watch.BOOTSTRAP_ERROR_BACKUP_COUNT + 1)

    records = watch.read_bootstrap_records(tmp_path)
    assert records, "records must exist for this to be a meaningful bound"
    assert all(record.get("status") == watch.STATUS_FINISHED for record in records)
    assert not any(record.get("status") == "failed" for record in records)

    live = watch.bootstrap_log_path()
    assert live.stat().st_size <= watch.BOOTSTRAP_ERROR_MAX_BYTES


def test_bounded_growth_assertions_fail_when_rotation_is_removed(monkeypatch, tmp_path) -> None:
    """Negative control: the bounded-growth test must fail without rotation.

    A cap test that passes whether or not the cap is enforced is not a test, it
    is a comment. Disabling rotation turns ``_append_record`` back into the
    unbounded append this change removed, so the very assertion the fix exists
    to satisfy must go red here.
    """
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(watch, "rotate_bootstrap_log", lambda *args, **kwargs: None)

    _fill_watch_log(monkeypatch, tmp_path, generations=2)

    live = watch.bootstrap_log_path()
    assert live.stat().st_size > watch.BOOTSTRAP_ERROR_MAX_BYTES, "with rotation disabled the log must exceed the cap"


def test_oversized_single_record_cannot_blow_a_generation(monkeypatch, tmp_path) -> None:
    """One record is bounded too, not just the file.

    Rotation bounds the file only while each append stays small: a multi-
    megabyte ``traceback`` would land in a single write and push a nearly empty
    file straight past the cap. The caps mirror core's ``host_errors``.
    """
    _isolate(monkeypatch, tmp_path)
    watch.record_bootstrap_finished(
        None,
        run_id="run-oversized",
        traceback="T" * (watch.MAX_TB_CHARS * 3),
        message="M" * (watch.MAX_MSG_CHARS * 3),
    )

    live = watch.bootstrap_log_path()
    assert live.stat().st_size <= watch.BOOTSTRAP_ERROR_MAX_BYTES
    (record,) = watch.read_bootstrap_records(tmp_path)
    assert len(record["traceback"]) < watch.MAX_TB_CHARS * 2
    assert record["traceback"].endswith("...[truncated]")
    assert len(record["message"]) < watch.MAX_MSG_CHARS * 2
    assert record["message"].endswith("...[truncated]")


def test_rotated_generations_read_oldest_first_after_watch_rotation(monkeypatch, tmp_path) -> None:
    """Watch-side rotation must not scramble the read order.

    ``read_bootstrap_records`` folds rotated generations back in oldest-first
    with the live file last. Now that the watch side rotates too, that ordering
    has to survive rotation performed by *this* writer, not just userSetup's.
    """
    _isolate(monkeypatch, tmp_path)
    _fill_watch_log(monkeypatch, tmp_path, generations=watch.BOOTSTRAP_ERROR_BACKUP_COUNT + 1)

    records = watch.read_bootstrap_records(tmp_path)
    sequences = [record["seq"] for record in records]

    assert len(sequences) > watch.BOOTSTRAP_ERROR_BACKUP_COUNT, "rotation must have happened"
    assert sequences == sorted(sequences), "records must read oldest-first, live file last"


def _is_docstring(node) -> bool:
    """True for a module docstring expression on both Python 3.7 and 3.8+.

    Python 3.7 parses a string literal as ``ast.Str``; 3.8+ folds it into
    ``ast.Constant``. The header probe below replays only ``userSetup.py``'s
    leading imports and constants, so it must skip the docstring on both or it
    ``break``s on line 1 and captures no constants at all -- making the very
    drift it exists to detect unobservable on the py3.7 red-line lane.
    """
    if not isinstance(node, _ast.Expr):
        return False
    value = node.value
    if isinstance(value, _ast.Constant):
        return isinstance(value.value, str)
    # ``ast.Str`` is removed in Python 3.14, so match by class name rather
    # than referencing the symbol (which keeps this importable there too).
    return type(value).__name__ == "Str"


def test_user_setup_and_watch_share_one_rotation_policy() -> None:
    """The two writers must agree on the cap, or one silently owns the bound.

    ``maya/userSetup.py`` sources before the adapter is importable, so it keeps
    literal fallbacks. If those drift from the adapter's constants, whichever
    half grows the file is no longer bounded by the value the other half
    enforces -- and the drift is invisible until the log is already huge.
    """
    source = USER_SETUP_PATH.read_text(encoding="utf-8")
    namespace = {"__name__": "_user_setup_policy_probe"}
    # Execute only the leading header -- imports and module-level constants.
    # The rest of the file defines functions and then *calls* them at import
    # time to drive the Maya load, so it cannot be executed here.
    tree = _ast.parse(source)
    header_nodes = []
    for node in tree.body:
        if _is_docstring(node):
            continue  # module docstring
        if not isinstance(node, (_ast.Import, _ast.ImportFrom, _ast.Assign)):
            break
        header_nodes.append(node)
    header = _ast.Module(body=header_nodes, type_ignores=[])
    exec(compile(header, str(USER_SETUP_PATH), "exec"), namespace)

    assert namespace["BOOTSTRAP_ERROR_MAX_BYTES"] == watch.BOOTSTRAP_ERROR_MAX_BYTES
    assert namespace["BOOTSTRAP_ERROR_BACKUP_COUNT"] == watch.BOOTSTRAP_ERROR_BACKUP_COUNT
    assert namespace["BOOTSTRAP_ERROR_MAX_TRACEBACK_CHARS"] == watch.MAX_TB_CHARS
    assert namespace["BOOTSTRAP_ERROR_MAX_MESSAGE_CHARS"] == watch.MAX_MSG_CHARS


def test_read_bootstrap_records_includes_rotated_generations(tmp_path) -> None:
    """Capping the log must not shrink what an operator can recover.

    ``maya/userSetup.py`` rotates ``userSetup-<date>.jsonl`` through numbered
    generations once it fills. Reading only ``*.jsonl`` would hide every
    rotated record from this public reader, so rotated history is folded back
    in -- oldest generation first, live file last.
    """
    log = tmp_path / "userSetup-20261005.jsonl"
    for generation, stage in ((2, "oldest"), (1, "older")):
        log.with_name("{}.{}".format(log.name, generation)).write_text(
            json.dumps({"stage": stage}) + "\n", encoding="utf-8"
        )
    log.write_text(json.dumps({"stage": "live"}) + "\n", encoding="utf-8")

    stages = [record["stage"] for record in watch.read_bootstrap_records(tmp_path)]

    assert stages == ["oldest", "older", "live"]
