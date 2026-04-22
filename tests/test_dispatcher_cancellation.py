"""Tests for cooperative cancellation, pump stats, and drain-on-stop.

Covers issue #85 (``check_maya_cancelled()``, ``MayaUiPump.stats``) and the
Maya-side half of issue #89 (``MayaUiDispatcher.shutdown`` + server
integration).
"""

from __future__ import annotations

import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

# Module under test
from dcc_mcp_maya.dispatcher import (
    DEFAULT_BUDGET_MS,
    OVERRUN_MULTIPLIER,
    MayaUiDispatcher,
    MayaUiPump,
    check_maya_cancelled,
)

# ---------------------------------------------------------------------------
# check_maya_cancelled() — core-token and per-job layers
# ---------------------------------------------------------------------------


def test_check_maya_cancelled_is_noop_outside_request():
    """Calling ``check_maya_cancelled`` with no context is a cheap no-op."""
    # Should not raise on a fresh interpreter with no token / job installed.
    check_maya_cancelled()


def test_check_maya_cancelled_honours_core_cancel_token():
    """Layer 1 — ``dcc_mcp_core.cancellation`` request token trips the probe."""
    from dcc_mcp_core.cancellation import (
        CancelledError,
        CancelToken,
        reset_cancel_token,
        set_cancel_token,
    )

    token = CancelToken()
    reset = set_cancel_token(token)
    try:
        check_maya_cancelled()  # token not yet cancelled
        token.cancel()
        with pytest.raises(CancelledError):
            check_maya_cancelled()
    finally:
        reset_cancel_token(reset)


def test_check_maya_cancelled_honours_dispatcher_flag_during_execute():
    """Layer 2 — ``MayaUiDispatcher.cancel`` trips the probe inside execute."""
    dispatcher = MayaUiDispatcher()

    iterations = []

    def long_task():
        # Simulate a loop that checks at every step — the second
        # iteration must raise after the dispatcher cancels us.
        for i in range(5):
            check_maya_cancelled()
            iterations.append(i)
            if i == 1:
                dispatcher.cancel("req-1")

    import_thread = threading.Thread(
        target=lambda: dispatcher.submit_callable("req-1", long_task, affinity="main", timeout_ms=2000),
    )
    import_thread.start()

    # Drain on this "UI" thread — the task runs here, inside the
    # context of :meth:`_JobEntry.execute`, so ``check_maya_cancelled``
    # sees the cancel flag set during execution.
    #
    # Give the submitter a moment to enqueue the job before we start
    # draining so the test is order-independent.
    for _ in range(20):
        if dispatcher.pending_count() > 0:
            break
        time.sleep(0.01)
    dispatcher.drain_queue(budget_ms=200)
    import_thread.join(timeout=2.0)

    # We walked at least into iteration 1 (where we triggered cancel),
    # but the loop must have aborted via CancelledError — so iteration 4
    # must NOT have executed.
    assert 1 in iterations
    assert 4 not in iterations


# ---------------------------------------------------------------------------
# MayaUiPump.stats — overrun_cycles + longest_job_ms
# ---------------------------------------------------------------------------


def test_pump_stats_record_overrun_cycles():
    """A single non-cooperative job that exceeds ``budget_ms * OVERRUN_MULTIPLIER``
    must increment ``overrun_cycles`` exactly once and update
    ``longest_job_ms`` with a sensible duration.
    """
    dispatcher = MayaUiDispatcher()
    pump = MayaUiPump(dispatcher, budget_ms=5.0)  # tight budget

    overrun_threshold_ms = pump.budget_ms * OVERRUN_MULTIPLIER

    def hog_the_ui():
        # Block longer than the overrun threshold to guarantee detection
        # across platforms with noisy schedulers. 4× the threshold keeps
        # the test fast while still exceeding OVERRUN_MULTIPLIER.
        time.sleep(overrun_threshold_ms / 1000.0 * 4.0)

    submitter_result = {}

    def submit():
        submitter_result.update(dispatcher.submit_callable("hog", hog_the_ui, affinity="main", timeout_ms=2000))

    t = threading.Thread(target=submit)
    t.start()
    # Wait for the job to show up in the main queue.
    for _ in range(50):
        if dispatcher.pending_count() > 0:
            break
        time.sleep(0.01)

    # Drive the idle-event callback directly — we cannot register a
    # scriptJob outside Maya.
    pump._pump_tick()  # noqa: SLF001
    t.join(timeout=3.0)

    stats = pump.stats
    assert stats["overrun_cycles"] == 1, stats
    assert stats["longest_job_ms"] >= overrun_threshold_ms, stats
    # Cumulative wall-clock must be consistent.
    assert stats["total_cycles"] == 1
    assert stats["total_executed"] == 1


def test_pump_stats_stay_zero_when_budget_honoured():
    dispatcher = MayaUiDispatcher()
    pump = MayaUiPump(dispatcher, budget_ms=DEFAULT_BUDGET_MS)

    def quick():
        # Nearly instant — well below DEFAULT_BUDGET_MS * 2.
        return 1

    submitter_result = {}

    def submit():
        submitter_result.update(dispatcher.submit_callable("quick", quick, affinity="main", timeout_ms=500))

    t = threading.Thread(target=submit)
    t.start()
    for _ in range(50):
        if dispatcher.pending_count() > 0:
            break
        time.sleep(0.01)
    pump._pump_tick()  # noqa: SLF001
    t.join(timeout=2.0)

    stats = pump.stats
    assert stats["overrun_cycles"] == 0, stats
    assert stats["total_executed"] == 1


# ---------------------------------------------------------------------------
# MayaUiDispatcher.shutdown — issue #89 partial coverage
# ---------------------------------------------------------------------------


def test_shutdown_unblocks_queued_submit_callable_quickly():
    """A thread blocked inside ``submit_callable`` must return within
    the usual ``event.wait()`` poll after :meth:`shutdown` fires.
    """
    dispatcher = MayaUiDispatcher()

    result_holder = {}

    def never_runs():
        pytest.fail("Queued task must not execute after shutdown()")

    def submit():
        result_holder["outcome"] = dispatcher.submit_callable("queued-1", never_runs, affinity="main", timeout_ms=5000)

    t = threading.Thread(target=submit)
    t.start()

    # Wait until the submitter has enqueued the job.
    for _ in range(50):
        if dispatcher.pending_count() > 0:
            break
        time.sleep(0.01)

    start = time.monotonic()
    signalled = dispatcher.shutdown("Interrupted")
    t.join(timeout=1.0)
    elapsed = time.monotonic() - start

    assert signalled >= 1
    assert not t.is_alive(), "submit_callable must unblock within 1 s of shutdown()"
    assert elapsed < 1.0
    outcome = result_holder["outcome"]
    assert outcome["success"] is False
    assert outcome["error"] == "Interrupted"


def test_shutdown_flags_running_job_for_cooperative_cancel():
    """A job that is already running observes the cancel flag via
    :func:`check_maya_cancelled` and exits with ``CancelledError``.
    """
    from dcc_mcp_core.cancellation import CancelledError

    dispatcher = MayaUiDispatcher()

    started = threading.Event()
    observed_cancel = threading.Event()

    def long_task():
        started.set()
        for _ in range(50):
            try:
                check_maya_cancelled()
            except CancelledError:
                observed_cancel.set()
                raise
            time.sleep(0.01)

    submit_thread = threading.Thread(
        target=lambda: dispatcher.submit_callable("long", long_task, affinity="main", timeout_ms=3000)
    )
    submit_thread.start()

    # Wait for submitter to enqueue the task.
    for _ in range(50):
        if dispatcher.pending_count() > 0:
            break
        time.sleep(0.01)

    def drive_pump():
        dispatcher.drain_queue(budget_ms=2000)

    pump_thread = threading.Thread(target=drive_pump)
    pump_thread.start()

    # Give the task a chance to start executing.
    assert started.wait(timeout=2.0), "task never started on main thread"

    dispatcher.shutdown("Interrupted")

    pump_thread.join(timeout=3.0)
    submit_thread.join(timeout=3.0)

    assert observed_cancel.is_set(), "cooperating task failed to observe cancel flag"


def test_submit_callable_after_shutdown_returns_immediately():
    """Post-shutdown submissions must not hang — issue #89 contract."""
    dispatcher = MayaUiDispatcher()
    dispatcher.shutdown("Interrupted")

    outcome = dispatcher.submit_callable("post", lambda: 1, affinity="main", timeout_ms=5000)
    assert outcome["success"] is False
    assert outcome["error"] == "Interrupted"


# ---------------------------------------------------------------------------
# MayaMcpServer.stop() wiring — partial #85 integration test
# ---------------------------------------------------------------------------


@pytest.fixture
def _mock_maya_modules():
    maya_mock = MagicMock()
    modules = {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": maya_mock.mel,
        "maya.utils": maya_mock.utils,
    }
    with patch.dict(sys.modules, modules):
        yield


def test_server_stop_drains_attached_dispatcher(_mock_maya_modules):
    """``MayaMcpServer.stop()`` must call ``dispatcher.shutdown`` so blocked
    threads unblock without hanging the server teardown.
    """
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    import importlib

    srv_mod = importlib.import_module("dcc_mcp_maya.server")
    dispatcher_mod = importlib.import_module("dcc_mcp_maya.dispatcher")

    server = srv_mod.MayaMcpServer(port=0)
    dispatcher = dispatcher_mod.MayaUiDispatcher()
    server.attach_dispatcher(dispatcher)
    server.start()

    # Prime the dispatcher with a queued job nobody will drain.
    outcomes = {}

    def submit():
        outcomes["outcome"] = dispatcher.submit_callable("queued", lambda: 42, affinity="main", timeout_ms=5000)

    t = threading.Thread(target=submit)
    t.start()
    for _ in range(50):
        if dispatcher.pending_count() > 0:
            break
        time.sleep(0.01)

    start = time.monotonic()
    server.stop()
    t.join(timeout=1.0)
    elapsed = time.monotonic() - start

    assert not t.is_alive(), "submit_callable must unblock when server stops"
    assert elapsed < 2.0
    assert dispatcher.is_shutdown is True
    assert outcomes["outcome"]["error"] == "Interrupted"
