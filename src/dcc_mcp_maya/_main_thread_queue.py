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
from concurrent.futures import Future
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

ENV_QUEUE_DEPTH = "DCC_MCP_MAYA_EXEC_QUEUE_DEPTH"
ENV_QUEUE_SUBMIT_TIMEOUT_SECS = "DCC_MCP_MAYA_EXEC_QUEUE_SUBMIT_TIMEOUT_SECS"

_DEFAULT_DEPTH = 64
_DEFAULT_SUBMIT_TIMEOUT_SECS = 30.0


class QueueFullError(RuntimeError):
    """Raised when ``submit`` cannot enqueue within the configured timeout."""


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

    def __init__(self, depth: Optional[int] = None) -> None:
        if depth is None:
            depth = _resolve_int_env(ENV_QUEUE_DEPTH, _DEFAULT_DEPTH)
        self._depth = max(1, int(depth))
        self._q: "queue.Queue[Any]" = queue.Queue(maxsize=self._depth)
        self._pump: Optional[threading.Thread] = None
        self._pump_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._submitted = 0
        self._completed = 0
        self._failed = 0
        self._rejected = 0
        self._metrics_lock = threading.Lock()

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
        return {
            "depth": self._q.qsize(),
            "maxsize": self._depth,
            "pump_alive": self._pump is not None and self._pump.is_alive(),
            "submitted": submitted,
            "completed": completed,
            "failed": failed,
            "rejected": rejected,
        }

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
            try:
                if future.set_running_or_notify_cancel():
                    result = self._run_on_main(fn)
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
    "MayaMainThreadQueue",
    "QueueFullError",
    "get_queue",
    "reset_for_tests",
]
