"""Unit tests for :mod:`dcc_mcp_maya._main_thread_queue`.

The queue is the **only** main-thread serialisation point under the
new ``execute_python`` (post #248). These tests cover the contract:

* single pump thread → FIFO-ish under racing producers, exactly-once
  delivery, no drops;
* bounded depth → ``QueueFullError`` surface, ``rejected`` counter
  increments;
* ``maya.utils`` unavailable → pump falls back to inline exec without
  poisoning callers;
* ``executeInMainThreadWithResult`` itself raising → same inline
  fallback;
* exceptions raised by user callables propagate to the caller's
  ``Future``;
* metrics counters (``submitted`` / ``completed`` / ``failed`` /
  ``rejected``) are accurate;
* ``shutdown()`` drains and stops the pump.

All tests use the singleton ``reset_for_tests()`` helper so they do
not bleed daemon threads into one another.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import threading
import time
from concurrent.futures import Future
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya import _main_thread_queue


@pytest.fixture(autouse=True)
def _reset_singleton():
    _main_thread_queue.reset_for_tests()
    yield
    _main_thread_queue.reset_for_tests()


class TestPumpFallbackPaths:
    """When Maya isn't available the pump must still serve jobs."""

    def test_pump_runs_inline_when_maya_utils_unavailable(self, monkeypatch):
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)
        q = _main_thread_queue.MayaMainThreadQueue()
        try:
            fut = q.submit(lambda: 7 * 6)
            assert fut.result(timeout=2.0) == 42
        finally:
            q.shutdown()

    def test_pump_falls_back_to_inline_when_bridge_raises(self, monkeypatch):
        fake_mu = MagicMock()
        fake_mu.executeInMainThreadWithResult.side_effect = RuntimeError("UI thread is gone")
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: fake_mu)

        q = _main_thread_queue.MayaMainThreadQueue()
        try:
            fut = q.submit(lambda: "ok")
            assert fut.result(timeout=2.0) == "ok"
            fake_mu.executeInMainThreadWithResult.assert_called()
        finally:
            q.shutdown()


class TestPumpErrorRelay:
    """User callable exceptions land on the caller's Future, not the pump."""

    def test_user_exception_propagates_via_future(self, monkeypatch):
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)
        q = _main_thread_queue.MayaMainThreadQueue()
        try:

            def boom():
                raise ValueError("intentional")

            fut = q.submit(boom)
            with pytest.raises(ValueError, match="intentional"):
                fut.result(timeout=2.0)
            # The pump kept running — a follow-up job must still complete.
            fut2 = q.submit(lambda: "alive")
            assert fut2.result(timeout=2.0) == "alive"
        finally:
            q.shutdown()

    def test_failed_metric_increments(self, monkeypatch):
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)
        q = _main_thread_queue.MayaMainThreadQueue()
        try:
            fut = q.submit(lambda: (_ for _ in ()).throw(RuntimeError("nope")))
            with pytest.raises(RuntimeError):
                fut.result(timeout=2.0)
            # Give the pump a beat to update its metrics counter.
            for _ in range(20):
                if q.status()["failed"] >= 1:
                    break
                time.sleep(0.01)
            assert q.status()["failed"] == 1
            assert q.status()["completed"] == 0
        finally:
            q.shutdown()


class TestBoundedDepth:
    """Floods must surface as backpressure, not silent stalls."""

    def test_full_queue_returns_queue_full_error_future(self, monkeypatch):
        # Stop the pump by patching the bridge to block forever.
        block_event = threading.Event()

        def blocking_marshal(fn):
            block_event.wait(timeout=5.0)
            return fn()

        fake_mu = MagicMock()
        fake_mu.executeInMainThreadWithResult.side_effect = blocking_marshal
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: fake_mu)

        q = _main_thread_queue.MayaMainThreadQueue(depth=2)
        try:
            # Job 1 enters the pump (it dequeues immediately, then blocks
            # inside ``executeInMainThreadWithResult`` waiting for
            # ``block_event``). Queue is empty.
            slow_fut = q.submit(lambda: "slow")
            # Give the pump a moment to dequeue.
            for _ in range(20):
                if q.status()["pump_alive"]:
                    break
                time.sleep(0.01)
            time.sleep(0.05)
            # Jobs 2 and 3 sit in the queue — pump is still blocked.
            fill_a = q.submit(lambda: "fill-a")
            fill_b = q.submit(lambda: "fill-b")
            # Queue is now at capacity (depth=2). The next submit must
            # back off after ``timeout`` and return a Future carrying
            # QueueFullError.
            reject_fut = q.submit(lambda: "reject", timeout=0.1)

            with pytest.raises(_main_thread_queue.QueueFullError):
                reject_fut.result(timeout=1.0)

            assert q.status()["rejected"] == 1
            # Releasing the pump must let the queued jobs complete.
            block_event.set()
            assert slow_fut.result(timeout=2.0) == "slow"
            assert fill_a.result(timeout=2.0) == "fill-a"
            assert fill_b.result(timeout=2.0) == "fill-b"
        finally:
            block_event.set()
            q.shutdown()


class TestConcurrentFIFO:
    """Many threads can submit concurrently; pump drains every job exactly once."""

    def test_no_drops_no_duplicates_under_burst(self, monkeypatch):
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)
        q = _main_thread_queue.MayaMainThreadQueue(depth=128)
        try:
            barrier = threading.Barrier(40)
            results: list = [None] * 40

            def worker(slot: int) -> None:
                barrier.wait()
                fut = q.submit(lambda s=slot: s * 2)
                results[slot] = fut.result(timeout=5.0)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

            assert results == [i * 2 for i in range(40)]
            status = q.status()
            assert status["submitted"] == 40
            assert status["completed"] == 40
            assert status["failed"] == 0
            assert status["rejected"] == 0
        finally:
            q.shutdown()


class TestWedgeDetectionAndDrain:
    """Wedge detection + ``drain_pending`` — the "kick the queue" path.

    User-reported scenario (2026-05-16): a user script wedged Maya's
    main thread; ``execute_python`` requests piled up behind it; MCP
    clients hung waiting on Futures that would never resolve.
    ``status()`` must surface the wedge so operators can SEE it; the
    ``drain_pending`` API must let them free the queued callers
    without first restarting Maya.
    """

    def test_status_reports_inflight_state(self, monkeypatch):
        """Status carries `in_flight_secs` + `wedged` while a job is on Maya."""
        # Force the pump to block on the marshal call so we can observe
        # the in-flight state mid-execution.
        block_event = threading.Event()

        def blocking_marshal(fn):
            block_event.wait(timeout=5.0)
            return fn()

        fake_mu = MagicMock()
        fake_mu.executeInMainThreadWithResult.side_effect = blocking_marshal
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: fake_mu)

        # Aggressive threshold so we observe `wedged=True` quickly.
        q = _main_thread_queue.MayaMainThreadQueue(depth=8, wedge_threshold_secs=0.1)
        try:
            fut = q.submit(lambda: "ok")
            # Let the pump dequeue + enter blocking_marshal.
            for _ in range(40):
                if q.status()["in_flight"]:
                    break
                time.sleep(0.01)
            assert q.status()["in_flight"] is True, "pump should be in-flight"
            # Wait well past the wedge threshold (0.1s) so the comparison
            # is unambiguous regardless of monotonic-clock granularity.
            time.sleep(0.35)
            wedged_snapshot = q.status()
            assert wedged_snapshot["wedged"] is True, (
                "should be flagged wedged, got {0!r}".format(wedged_snapshot)
            )
            assert wedged_snapshot["in_flight_secs"] is not None
            assert wedged_snapshot["in_flight_secs"] >= 0.1

            # Release the pump; in_flight clears.
            block_event.set()
            assert fut.result(timeout=2.0) == "ok"
            cleared = q.status()
            assert cleared["in_flight"] is False
            assert cleared["wedged"] is False
            assert cleared["in_flight_secs"] is None
        finally:
            block_event.set()
            q.shutdown()

    def test_drain_pending_cancels_queued_jobs_with_wedge_error(self, monkeypatch):
        """``drain_pending`` frees queued callers but does NOT touch the in-flight job."""
        block_event = threading.Event()

        def blocking_marshal(fn):
            block_event.wait(timeout=5.0)
            return fn()

        fake_mu = MagicMock()
        fake_mu.executeInMainThreadWithResult.side_effect = blocking_marshal
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: fake_mu)

        q = _main_thread_queue.MayaMainThreadQueue(depth=4)
        try:
            # Job 1 enters the pump, blocks on the bridge.
            in_flight = q.submit(lambda: "in_flight")
            for _ in range(40):
                if q.status()["in_flight"]:
                    break
                time.sleep(0.01)
            assert q.status()["in_flight"] is True

            # Jobs 2 & 3 sit in the queue behind the wedge.
            queued_a = q.submit(lambda: "a")
            queued_b = q.submit(lambda: "b")
            assert q.status()["depth"] == 2

            # Drain — must cancel the queued ones, not the in-flight.
            cancelled = q.drain_pending(reason="test-drain")
            assert cancelled == 2

            with pytest.raises(_main_thread_queue.WedgeDetectedError, match="test-drain"):
                queued_a.result(timeout=1.0)
            with pytest.raises(_main_thread_queue.WedgeDetectedError, match="test-drain"):
                queued_b.result(timeout=1.0)

            # The in-flight future must STILL be running.
            assert not in_flight.done(), "drain must not touch the in-flight job"

            # Metrics reflect the drain.
            status = q.status()
            assert status["drained"] >= 2
            assert status["depth"] == 0

            # Release and confirm the in-flight job completes normally.
            block_event.set()
            assert in_flight.result(timeout=2.0) == "in_flight"
        finally:
            block_event.set()
            q.shutdown()

    def test_drain_pending_on_empty_queue_returns_zero(self):
        q = _main_thread_queue.MayaMainThreadQueue()
        try:
            assert q.drain_pending() == 0
            assert q.status()["drained"] == 0
        finally:
            q.shutdown()


class TestStatusAndShutdown:
    """``status()`` must reflect the pump's state. ``shutdown()`` joins cleanly."""

    def test_status_initial_state(self):
        q = _main_thread_queue.MayaMainThreadQueue(depth=8, wedge_threshold_secs=60.0)
        try:
            status = q.status()
            assert status["depth"] == 0
            assert status["maxsize"] == 8
            assert status["pump_alive"] is False  # pump is lazy
            assert status["submitted"] == 0
            assert status["completed"] == 0
            assert status["failed"] == 0
            assert status["rejected"] == 0
            assert status["drained"] == 0
            assert status["wedge_warnings"] == 0
            assert status["in_flight"] is False
            assert status["in_flight_secs"] is None
            assert status["wedged"] is False
            assert status["wedge_threshold_secs"] == 60.0
        finally:
            q.shutdown()

    def test_status_after_submit(self, monkeypatch):
        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)
        q = _main_thread_queue.MayaMainThreadQueue()
        try:
            fut = q.submit(lambda: 1)
            assert fut.result(timeout=2.0) == 1
            status = q.status()
            assert status["pump_alive"] is True
            assert status["submitted"] == 1
            assert status["completed"] == 1
        finally:
            q.shutdown()

    def test_singleton_reset_replaces_queue(self):
        q1 = _main_thread_queue.get_queue()
        q2 = _main_thread_queue.get_queue()
        assert q1 is q2  # same singleton across the call boundary

        _main_thread_queue.reset_for_tests()
        q3 = _main_thread_queue.get_queue()
        assert q3 is not q1

    def test_submit_returns_future_instance(self):
        q = _main_thread_queue.MayaMainThreadQueue()
        try:
            fut = q.submit(lambda: None, timeout=0.1)
            assert isinstance(fut, Future)
        finally:
            q.shutdown()
