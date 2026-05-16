"""Single-writer queue for Maya main-thread work.

Why this exists
===============

``execute_python`` from the MCP HTTP server arrives on a tokio worker
thread. The fix in ``b9ded57f`` made it call
``maya.utils.executeInMainThreadWithResult`` so user code runs on
Maya's UI thread. That call **blocks the worker** until the main
thread finishes the job.

With N concurrent ``POST /v1/call`` requests, every one of them
would call ``executeInMainThreadWithResult`` from its own tokio
worker. The tokio pool is finite (usually ~CPU count). Once it is
exhausted, new requests stall at TCP accept time, and the ordering
of Maya-side execution is loosely tied to whichever worker the
scheduler resumes first.

This module collapses that fan-in to a **single pump thread**:

* Every caller submits a no-arg callable and waits on a
  :class:`~concurrent.futures.Future`.
* One pump thread dequeues jobs and calls
  ``maya.utils.executeInMainThreadWithResult`` strictly FIFO.
* The queue has a bounded depth (``DCC_MCP_MAYA_EXEC_QUEUE_DEPTH``,
  default 64). When full, ``submit`` rejects the job with a clear
  envelope so the gateway can surface backpressure to the agent
  instead of dropping it on the floor.
* ``status()`` reports queue depth + pump health for diagnostics.

What it does NOT solve
======================

* **Worker thread exhaustion** — every MCP handler is still
  synchronous from Python's perspective, so it has to wait on
  ``Future.result()``. The tokio worker stays blocked while waiting.
  The win here is **FIFO predictability and a single in-flight
  marshalling call**, not concurrency scaling.
* **Cancellation of in-flight jobs** — once a job has been handed
  off to Maya's main thread via ``executeInMainThreadWithResult``,
  it runs to completion. Cancellation of *queued* jobs IS supported
  via the returned ``Future``; cancellation of running jobs is a
  follow-up.

Fallback path
=============

When ``maya.utils`` cannot be imported (``mayapy`` / pytest), the
pump silently runs jobs inline (no thread switch). The queue still
serialises across callers; the only thing missing is the main-thread
marshalling primitive itself.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import queue
import threading
import time
from concurrent.futures import Future
from typing import Any, Callable, Optional


def _monotonic_now() -> float:
    """Wall-clock-free timestamp for in-flight tracking + wedge detection."""
    return time.monotonic()


logger = logging.getLogger(__name__)

ENV_QUEUE_DEPTH = "DCC_MCP_MAYA_EXEC_QUEUE_DEPTH"
ENV_QUEUE_SUBMIT_TIMEOUT_SECS = "DCC_MCP_MAYA_EXEC_QUEUE_SUBMIT_TIMEOUT_SECS"
ENV_WEDGE_THRESHOLD_SECS = "DCC_MCP_MAYA_WEDGE_THRESHOLD_SECS"

_DEFAULT_DEPTH = 64
_DEFAULT_SUBMIT_TIMEOUT_SECS = 30.0
#: Default threshold (seconds) before the in-flight main-thread job is
#: considered "wedged" — Maya's UI thread has not returned from
#: ``executeInMainThreadWithResult`` for this long. Status reports flip
#: ``wedged`` to True and drain operations name this in their envelopes.
#: We cannot interrupt the wedged job (Maya's main thread is
#: cooperative, not pre-emptive), but we CAN free new callers and
#: surface a clear signal so operators know to look at Maya.
_DEFAULT_WEDGE_THRESHOLD_SECS = 60.0


class QueueFullError(RuntimeError):
    """Raised when ``submit`` cannot enqueue within the configured timeout."""


class WedgeDetectedError(RuntimeError):
    """Raised when a queued job is drained because the pump is wedged.

    The job never ran on Maya's main thread. The in-flight job (the one
    actually wedging the pump) is NOT failed by drain — Maya's main
    thread is non-preemptive, so the bytes are still executing there
    and will eventually complete (or wait until Maya is killed). All
    we can do is free the queued callers and tell them what happened.
    """


def _resolve_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _resolve_float_env(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _import_maya_utils() -> Any:
    """Return ``maya.utils`` or ``None`` (mayapy/pytest fallback)."""
    try:
        import maya.utils as mu  # noqa: PLC0415
    except ImportError:
        return None
    return mu


class MayaMainThreadQueue:
    """Bounded FIFO queue with a single pump thread.

    Lazily starts its pump on the first ``submit`` so importing this
    module from pytest / ``mayapy`` does not spawn a daemon thread
    until anyone actually uses it.
    """

    def __init__(
        self,
        depth: Optional[int] = None,
        wedge_threshold_secs: Optional[float] = None,
    ) -> None:
        if depth is None:
            depth = _resolve_int_env(ENV_QUEUE_DEPTH, _DEFAULT_DEPTH)
        if wedge_threshold_secs is None:
            wedge_threshold_secs = _resolve_float_env(ENV_WEDGE_THRESHOLD_SECS, _DEFAULT_WEDGE_THRESHOLD_SECS)
        self._depth = max(1, int(depth))
        # Floor at 10 ms so the floor matters only for absurdly low
        # values (programmer error) — 1 s would block fast unit tests
        # from exercising the wedge path with reasonable timing.
        self._wedge_threshold_secs = max(0.01, float(wedge_threshold_secs))
        self._q: "queue.Queue[Any]" = queue.Queue(maxsize=self._depth)
        self._pump: Optional[threading.Thread] = None
        self._pump_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._submitted = 0
        self._completed = 0
        self._failed = 0
        self._rejected = 0
        self._drained = 0
        self._wedge_warnings = 0
        self._metrics_lock = threading.Lock()
        # Track the in-flight job's start time so external callers can
        # detect "the pump has been blocked in executeInMainThreadWithResult
        # for too long" without sneaking into private state. Lock-guarded
        # because the pump thread writes and any thread can read.
        self._inflight_started_monotonic: Optional[float] = None
        self._inflight_lock = threading.Lock()

    @property
    def maxsize(self) -> int:
        return self._depth

    @property
    def depth(self) -> int:
        return self._q.qsize()

    def status(self) -> dict:
        with self._metrics_lock:
            submitted = self._submitted
            completed = self._completed
            failed = self._failed
            rejected = self._rejected
            drained = self._drained
            wedge_warnings = self._wedge_warnings
        with self._inflight_lock:
            started = self._inflight_started_monotonic
        inflight_secs: Optional[float] = None
        wedged = False
        if started is not None:
            inflight_secs = round(_monotonic_now() - started, 2)
            wedged = inflight_secs > self._wedge_threshold_secs
        return {
            "depth": self._q.qsize(),
            "maxsize": self._depth,
            "pump_alive": self._pump is not None and self._pump.is_alive(),
            "submitted": submitted,
            "completed": completed,
            "failed": failed,
            "rejected": rejected,
            "drained": drained,
            "wedge_warnings": wedge_warnings,
            "in_flight": started is not None,
            "in_flight_secs": inflight_secs,
            "wedged": wedged,
            "wedge_threshold_secs": self._wedge_threshold_secs,
        }

    def drain_pending(self, reason: str = "drain requested") -> int:
        """Cancel every QUEUED (not in-flight) job with :class:`WedgeDetectedError`.

        Used to "kick the queue" when the in-flight job has wedged
        Maya's main thread and new MCP requests are piling up behind
        it. The in-flight job is NOT cancelled — Maya's main thread is
        cooperative, not pre-emptive, so the bytes already on the UI
        thread keep running until they return naturally (or Maya is
        killed). Drain only frees the callers waiting behind that job.

        Returns the number of jobs cancelled. Safe to call repeatedly
        and from any thread.
        """
        cancelled = 0
        # Drain whatever is currently in the queue. New submissions
        # during this loop will land after the drain window — they
        # will queue normally and pile up again if the wedge persists,
        # so operators can re-drain until Maya recovers.
        while True:
            try:
                item = self._q.get_nowait()
            except queue.Empty:
                break
            if item is None or item[0] is None:
                # Re-queue the shutdown sentinel; it must outlive drain.
                try:
                    self._q.put_nowait(item)
                except queue.Full:
                    pass
                self._q.task_done()
                break
            _fn, future = item
            try:
                if not future.done() and future.set_running_or_notify_cancel():
                    future.set_exception(WedgeDetectedError(reason))
                    cancelled += 1
            finally:
                self._q.task_done()
        if cancelled > 0:
            with self._metrics_lock:
                self._drained += cancelled
            logger.warning(
                "Maya main-thread queue: drained %d queued job(s) (%s)",
                cancelled,
                reason,
            )
        return cancelled

    def submit(self, fn: Callable[[], Any], timeout: Optional[float] = None) -> "Future[Any]":
        """Enqueue ``fn`` and return a Future for its result.

        ``fn`` must be a no-arg callable — it will be invoked by the
        pump thread under ``maya.utils.executeInMainThreadWithResult``
        so the call ends up on Maya's UI thread.

        When the queue is full, ``submit`` blocks for up to ``timeout``
        seconds waiting for room. If still full after the timeout, a
        completed-with-exception Future is returned carrying
        :class:`QueueFullError`. Callers should surface that as a
        backpressure envelope rather than retrying tight.
        """
        if timeout is None:
            timeout = _resolve_float_env(ENV_QUEUE_SUBMIT_TIMEOUT_SECS, _DEFAULT_SUBMIT_TIMEOUT_SECS)
        future: "Future[Any]" = Future()
        self._ensure_pump()
        try:
            self._q.put((fn, future), block=True, timeout=timeout if timeout > 0 else 0.001)
        except queue.Full:
            with self._metrics_lock:
                self._rejected += 1
            future.set_exception(
                QueueFullError(
                    "Maya main-thread queue full (depth={0}, maxsize={1}); "
                    "back off and retry. Configure with {2}.".format(self._q.qsize(), self._depth, ENV_QUEUE_DEPTH)
                )
            )
            return future
        with self._metrics_lock:
            self._submitted += 1
        return future

    def shutdown(self, timeout: float = 2.0) -> None:
        """Signal the pump to stop and wait for it to drain. Test-only."""
        self._stop_event.set()
        # Wake the pump if it is blocked on Queue.get with a sentinel.
        try:
            self._q.put_nowait((None, None))
        except queue.Full:
            pass
        if self._pump is not None:
            self._pump.join(timeout=timeout)
        self._stop_event.clear()
        self._pump = None

    # ── internals ─────────────────────────────────────────────────────

    def _ensure_pump(self) -> None:
        if self._pump is not None and self._pump.is_alive():
            return
        with self._pump_lock:
            if self._pump is not None and self._pump.is_alive():
                return
            self._stop_event.clear()
            self._pump = threading.Thread(
                target=self._loop,
                name="dcc-mcp-maya-mainthread-pump",
                daemon=True,
            )
            self._pump.start()

    def _loop(self) -> None:
        """Pump worker — drains the queue, marshals each job to Maya's main thread."""
        while not self._stop_event.is_set():
            try:
                item = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None or item[0] is None:
                # Shutdown sentinel.
                self._q.task_done()
                return
            fn, future = item
            # drain_pending may have already set the result/exception on
            # this future before we got it (race: drain pops, marks
            # cancelled, then pump picks). Skip those.
            if future.done():
                self._q.task_done()
                continue
            try:
                if future.set_running_or_notify_cancel():
                    with self._inflight_lock:
                        self._inflight_started_monotonic = _monotonic_now()
                    try:
                        result = self._run_on_main(fn)
                    finally:
                        with self._inflight_lock:
                            self._inflight_started_monotonic = None
                    future.set_result(result)
                # If the future was already cancelled, just drop it.
            except BaseException as exc:  # noqa: BLE001 — relay via Future
                future.set_exception(exc)
                with self._metrics_lock:
                    self._failed += 1
            else:
                with self._metrics_lock:
                    self._completed += 1
            finally:
                self._q.task_done()

    def note_wedge_warning(self) -> None:
        """Increment the wedge-warning counter. Called by external watchdogs."""
        with self._metrics_lock:
            self._wedge_warnings += 1

    def _run_on_main(self, fn: Callable[[], Any]) -> Any:
        """Marshal ``fn`` onto Maya's main thread via ``executeInMainThreadWithResult``.

        Falls back to inline execution when ``maya.utils`` is not
        importable — that path is reached from pytest / mayapy where
        there is no separate UI thread to defer to.
        """
        mu = _import_maya_utils()
        if mu is None:
            return fn()
        try:
            return mu.executeInMainThreadWithResult(fn)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "executeInMainThreadWithResult failed (%s); falling back to inline exec",
                exc,
            )
            return fn()


_singleton_lock = threading.Lock()
_singleton: Optional[MayaMainThreadQueue] = None


def get_queue() -> MayaMainThreadQueue:
    """Return the process-wide :class:`MayaMainThreadQueue` singleton."""
    global _singleton
    if _singleton is not None:
        return _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = MayaMainThreadQueue()
    return _singleton


def reset_for_tests() -> None:
    """Replace the singleton with a fresh queue. Test-only."""
    global _singleton
    with _singleton_lock:
        if _singleton is not None:
            try:
                _singleton.shutdown(timeout=1.0)
            except Exception:  # noqa: BLE001
                pass
        _singleton = None


__all__ = [
    "ENV_QUEUE_DEPTH",
    "ENV_QUEUE_SUBMIT_TIMEOUT_SECS",
    "ENV_WEDGE_THRESHOLD_SECS",
    "MayaMainThreadQueue",
    "QueueFullError",
    "WedgeDetectedError",
    "get_queue",
    "reset_for_tests",
]
