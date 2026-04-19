"""Maya thread-affinity dispatchers.

Provides Maya-specific implementations of the host-dispatcher pattern
defined in ``dcc-mcp-core`` (``crates/dcc-mcp-process/src/dispatcher.rs``).

Three dispatchers are provided:

:class:`MayaUiDispatcher`
    For interactive Maya sessions.  Routes ``Main``-affinity jobs through
    ``maya.utils.executeDeferred`` so they execute on Maya's UI thread.
    ``Any``-affinity jobs run on a background thread.

:class:`MayaStandaloneDispatcher`
    For ``mayapy`` / batch-render contexts where there is no event loop.
    All jobs execute directly on the calling thread.

:class:`MayaUiPump`
    A cooperative time-slice scheduler registered via
    ``cmds.scriptJob(event=['idle', pump])``.  Drains the pending
    main-thread job queue up to a configurable ``budget_ms`` per idle
    tick, then yields back to Maya so the viewport stays responsive.

Usage inside the plugin::

    from dcc_mcp_maya.dispatcher import MayaUiDispatcher, MayaUiPump

    dispatcher = MayaUiDispatcher()
    pump = MayaUiPump(dispatcher, budget_ms=8)
    pump.install()  # registers scriptJob

    # Submit work
    result = dispatcher.submit("create_sphere", payload='{"r":1}', affinity="main")
    # result: {"request_id": ..., "success": True, "output": ..., ...}

    pump.uninstall()  # removes scriptJob

See: https://github.com/loonghao/dcc-mcp-maya/issues/66
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

#: Default time budget (milliseconds) per idle-event pump cycle.
DEFAULT_BUDGET_MS = 8

#: Default soft timeout for individual jobs (milliseconds).
DEFAULT_JOB_TIMEOUT_MS = 30_000


# ── Job types ─────────────────────────────────────────────────────────────────


class _JobEntry:
    """Internal job wrapper queued for main-thread execution."""

    __slots__ = ("request_id", "affinity", "task", "timeout_ms", "event", "outcome")

    def __init__(
        self,
        request_id: str,
        affinity: str,
        task: Callable[[], Any],
        timeout_ms: Optional[int] = None,
    ) -> None:
        self.request_id = request_id
        self.affinity = affinity
        self.task = task
        self.timeout_ms = timeout_ms or DEFAULT_JOB_TIMEOUT_MS
        self.event = threading.Event()
        self.outcome: Optional[Dict[str, Any]] = None

    def execute(self) -> Dict[str, Any]:
        """Execute the task and populate ``self.outcome``."""
        try:
            output = self.task()
            self.outcome = {
                "request_id": self.request_id,
                "affinity": self.affinity,
                "success": True,
                "output": output,
                "error": None,
            }
        except Exception as exc:
            self.outcome = {
                "request_id": self.request_id,
                "affinity": self.affinity,
                "success": False,
                "output": None,
                "error": str(exc),
            }
        self.event.set()
        return self.outcome


# ── MayaUiDispatcher ─────────────────────────────────────────────────────────


class MayaUiDispatcher:
    """Thread-affinity aware dispatcher for interactive Maya sessions.

    - ``"main"`` affinity jobs are queued and executed on Maya's UI thread
      via :class:`MayaUiPump` (or a one-shot ``executeDeferred`` fallback).
    - ``"any"`` affinity jobs run immediately on a background thread.

    This class is **thread-safe**: ``submit()`` can be called from any thread.
    """

    def __init__(self) -> None:
        self._main_queue: Deque[_JobEntry] = deque()
        self._lock = threading.Lock()
        self._cancelled: set = set()

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(
        self,
        action_name: str,
        payload: Optional[str] = None,
        affinity: str = "any",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Submit a job and block until completion.

        Parameters
        ----------
        action_name:
            Logical action identifier (used as ``request_id``).
        payload:
            Opaque payload string returned in the output on success.
        affinity:
            ``"any"`` (default) or ``"main"``.
        timeout_ms:
            Soft timeout in milliseconds for the job.

        Returns
        -------
        dict
            ``{"request_id", "affinity", "success", "output", "error"}``
        """
        affinity = affinity.lower()
        if affinity not in ("any", "main"):
            return {
                "request_id": action_name,
                "affinity": affinity,
                "success": False,
                "output": None,
                "error": f"Unsupported affinity '{affinity}'; expected 'any' or 'main'",
            }

        def _task():
            return payload

        if affinity == "any":
            return self._run_any(action_name, _task, affinity)

        return self._submit_main(action_name, _task, affinity, timeout_ms)

    def submit_callable(
        self,
        request_id: str,
        task: Callable[[], Any],
        affinity: str = "main",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Submit an arbitrary callable for execution.

        Unlike :meth:`submit`, this accepts a real callable instead of a
        static payload string.  Intended for internal use by the MCP server
        when dispatching tool handlers.

        Parameters
        ----------
        request_id:
            Unique request identifier.
        task:
            Zero-argument callable executed on the target thread.
        affinity:
            ``"any"`` or ``"main"``.
        timeout_ms:
            Soft timeout in milliseconds.

        Returns
        -------
        dict
            Same structure as :meth:`submit`.
        """
        affinity = affinity.lower()
        if affinity == "any":
            return self._run_any(request_id, task, affinity)
        return self._submit_main(request_id, task, affinity, timeout_ms)

    def cancel(self, request_id: str) -> bool:
        """Cancel a pending main-thread job.

        Returns ``True`` if the job was found and removed from the queue.
        Jobs already executing cannot be cancelled.
        """
        with self._lock:
            self._cancelled.add(request_id)
            for job in self._main_queue:
                if job.request_id == request_id:
                    job.outcome = {
                        "request_id": request_id,
                        "affinity": job.affinity,
                        "success": False,
                        "output": None,
                        "error": "Cancelled",
                    }
                    job.event.set()
                    return True
        return False

    def pending_count(self) -> int:
        """Return the number of jobs waiting in the main-thread queue."""
        return len(self._main_queue)

    def supported(self) -> List[str]:
        """Return supported affinity values."""
        return ["any", "main"]

    def capabilities(self) -> Dict[str, bool]:
        """Return capability flags matching the Rust ``HostCapabilities`` shape."""
        return {
            "supports_main_thread": True,
            "supports_named_threads": False,
            "supports_any_thread": True,
            "supports_time_slicing": True,
        }

    # ── Queue access (used by MayaUiPump) ─────────────────────────────────────

    def drain_queue(self, budget_ms: float) -> Tuple[int, int]:
        """Execute queued main-thread jobs up to *budget_ms*.

        Called by :class:`MayaUiPump` on Maya's idle event.

        Returns
        -------
        tuple[int, int]
            ``(executed, remaining)`` counts.
        """
        executed = 0
        start = time.monotonic()
        deadline = start + (budget_ms / 1000.0)

        while time.monotonic() < deadline:
            job = self._dequeue()
            if job is None:
                break

            # Check cancellation
            with self._lock:
                if job.request_id in self._cancelled:
                    self._cancelled.discard(job.request_id)
                    if not job.event.is_set():
                        job.outcome = {
                            "request_id": job.request_id,
                            "affinity": job.affinity,
                            "success": False,
                            "output": None,
                            "error": "Cancelled",
                        }
                        job.event.set()
                    continue

            job.execute()
            executed += 1

        remaining = len(self._main_queue)
        if executed > 0:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.debug(
                "MayaUiPump: drained %d job(s) in %.1f ms, %d remaining",
                executed,
                elapsed_ms,
                remaining,
            )
        return executed, remaining

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _run_any(request_id: str, task: Callable, affinity: str) -> Dict[str, Any]:
        """Execute a job directly on the current thread (any affinity)."""
        try:
            output = task()
            return {
                "request_id": request_id,
                "affinity": affinity,
                "success": True,
                "output": output,
                "error": None,
            }
        except Exception as exc:
            return {
                "request_id": request_id,
                "affinity": affinity,
                "success": False,
                "output": None,
                "error": str(exc),
            }

    def _submit_main(
        self,
        request_id: str,
        task: Callable,
        affinity: str,
        timeout_ms: Optional[int],
    ) -> Dict[str, Any]:
        """Enqueue a job for main-thread execution and wait for completion."""
        job = _JobEntry(request_id, affinity, task, timeout_ms)

        with self._lock:
            self._main_queue.append(job)

        # If no MayaUiPump is installed, fall back to executeDeferred
        self._maybe_poke_deferred()

        timeout_sec = (timeout_ms or DEFAULT_JOB_TIMEOUT_MS) / 1000.0
        if not job.event.wait(timeout=timeout_sec):
            return {
                "request_id": request_id,
                "affinity": affinity,
                "success": False,
                "output": None,
                "error": f"Timeout ({timeout_sec:.1f}s) waiting for main-thread execution",
            }

        return job.outcome or {
            "request_id": request_id,
            "affinity": affinity,
            "success": False,
            "output": None,
            "error": "Job completed but outcome was not set",
        }

    def _dequeue(self) -> Optional[_JobEntry]:
        """Pop the next job from the main queue (thread-safe)."""
        with self._lock:
            if self._main_queue:
                return self._main_queue.popleft()
        return None

    def _maybe_poke_deferred(self) -> None:
        """Nudge Maya to drain the queue if no pump is installed.

        Uses ``maya.utils.executeDeferred`` as a one-shot fallback.
        The pump (``MayaUiPump``) is more efficient for sustained throughput.
        """
        try:
            import maya.utils  # noqa: PLC0415

            maya.utils.executeDeferred(self._deferred_drain)
        except ImportError:
            # Not running inside Maya — jobs will be drained manually
            pass
        except Exception:
            pass

    def _deferred_drain(self) -> None:
        """Drain all pending main-thread jobs (one-shot fallback)."""
        self.drain_queue(budget_ms=50)


# ── MayaStandaloneDispatcher ─────────────────────────────────────────────────


class MayaStandaloneDispatcher:
    """Dispatcher for ``mayapy`` / batch-render contexts.

    All jobs execute directly on the calling thread — there is no event
    loop, no idle callbacks, and no notion of a "main thread" distinct from
    the caller.  This is the right choice for:

    - ``mayapy`` standalone scripts
    - ``Render.exe`` contexts
    - ``maya -batch`` mode
    """

    def submit(
        self,
        action_name: str,
        payload: Optional[str] = None,
        affinity: str = "any",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a job synchronously on the calling thread.

        The *affinity* parameter is accepted but ignored — standalone mode
        has no thread scheduling.
        """
        return {
            "request_id": action_name,
            "affinity": affinity,
            "success": True,
            "output": payload,
            "error": None,
        }

    def submit_callable(
        self,
        request_id: str,
        task: Callable[[], Any],
        affinity: str = "any",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a callable synchronously."""
        try:
            output = task()
            return {
                "request_id": request_id,
                "affinity": affinity,
                "success": True,
                "output": output,
                "error": None,
            }
        except Exception as exc:
            return {
                "request_id": request_id,
                "affinity": affinity,
                "success": False,
                "output": None,
                "error": str(exc),
            }

    def supported(self) -> List[str]:
        """Return supported affinity values."""
        return ["any", "main"]

    def capabilities(self) -> Dict[str, bool]:
        """Return capability flags."""
        return {
            "supports_main_thread": True,
            "supports_named_threads": False,
            "supports_any_thread": True,
            "supports_time_slicing": False,
        }


# ── MayaUiPump ───────────────────────────────────────────────────────────────


class MayaUiPump:
    """Cooperative time-slice scheduler driven by Maya's idle event.

    Registers a ``scriptJob(event=['idle', pump], protected=True)`` that
    fires each time Maya becomes idle.  The pump drains pending main-thread
    jobs from the attached :class:`MayaUiDispatcher` up to *budget_ms*
    milliseconds, then yields back to Maya so the viewport stays responsive.

    Parameters
    ----------
    dispatcher:
        The :class:`MayaUiDispatcher` whose main-thread queue to drain.
    budget_ms:
        Maximum milliseconds to spend draining per idle tick.  Lower
        values preserve more UI responsiveness; higher values improve
        throughput for long-running chains of small operations.
    """

    def __init__(
        self,
        dispatcher: MayaUiDispatcher,
        budget_ms: float = DEFAULT_BUDGET_MS,
    ) -> None:
        self._dispatcher = dispatcher
        self._budget_ms = budget_ms
        self._script_job_id: Optional[int] = None
        self._installed = False
        self._stats = {"total_executed": 0, "total_cycles": 0, "total_elapsed_ms": 0.0}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_installed(self) -> bool:
        """``True`` if the idle scriptJob is currently active."""
        return self._installed

    @property
    def budget_ms(self) -> float:
        """Current time budget per idle-event cycle."""
        return self._budget_ms

    @budget_ms.setter
    def budget_ms(self, value: float) -> None:
        self._budget_ms = max(1.0, value)

    @property
    def stats(self) -> Dict[str, Any]:
        """Cumulative pump statistics."""
        return dict(self._stats)

    def install(self) -> bool:
        """Register the idle-event scriptJob with Maya.

        Returns ``True`` if installation succeeded or is already installed.
        """
        if self._installed:
            return True

        try:
            import maya.cmds as cmds  # noqa: PLC0415

            self._script_job_id = cmds.scriptJob(
                event=["idle", self._pump_tick],
                protected=True,
            )
            self._installed = True
            logger.info(
                "MayaUiPump installed (scriptJob=%d, budget=%.1f ms)",
                self._script_job_id,
                self._budget_ms,
            )
            return True
        except ImportError:
            logger.warning("MayaUiPump: maya.cmds not available — install skipped")
            return False
        except Exception as exc:
            logger.error("MayaUiPump: failed to install scriptJob: %s", exc)
            return False

    def uninstall(self) -> None:
        """Remove the idle-event scriptJob from Maya."""
        if not self._installed:
            return

        try:
            import maya.cmds as cmds  # noqa: PLC0415

            if self._script_job_id is not None:
                cmds.scriptJob(kill=self._script_job_id, force=True)
                logger.info("MayaUiPump uninstalled (scriptJob=%d)", self._script_job_id)
        except Exception as exc:
            logger.warning("MayaUiPump: error removing scriptJob: %s", exc)
        finally:
            self._script_job_id = None
            self._installed = False

    # ── Pump implementation ───────────────────────────────────────────────────

    def _pump_tick(self) -> None:
        """Idle-event callback: drain pending jobs within the budget."""
        start = time.monotonic()
        executed, remaining = self._dispatcher.drain_queue(self._budget_ms)

        elapsed_ms = (time.monotonic() - start) * 1000.0
        self._stats["total_executed"] += executed
        self._stats["total_cycles"] += 1
        self._stats["total_elapsed_ms"] += elapsed_ms

        if remaining > 0:
            # Re-poke Maya so we get another idle event quickly
            try:
                import maya.cmds as cmds  # noqa: PLC0415

                cmds.refresh(force=True)
            except Exception:
                pass


# ── Factory helper ────────────────────────────────────────────────────────────


def create_dispatcher(
    budget_ms: float = DEFAULT_BUDGET_MS,
) -> Tuple[Any, Optional[MayaUiPump]]:
    """Create the appropriate dispatcher for the current Maya environment.

    Returns
    -------
    tuple[MayaUiDispatcher | MayaStandaloneDispatcher, MayaUiPump | None]
        A ``(dispatcher, pump)`` pair.  The pump is ``None`` in standalone mode.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        is_batch = cmds.about(batch=True)
    except ImportError:
        is_batch = True

    if is_batch:
        return MayaStandaloneDispatcher(), None

    dispatcher = MayaUiDispatcher()
    pump = MayaUiPump(dispatcher, budget_ms=budget_ms)
    return dispatcher, pump
