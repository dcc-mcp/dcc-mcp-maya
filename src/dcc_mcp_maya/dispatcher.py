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
import contextvars
import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Core dispatcher re-exports ────────────────────────────────────────────────
# dcc-mcp-core 0.14.14 ships ``PyPumpedDispatcher`` (Rust-backed, main-thread
# pump) and ``PyStandaloneDispatcher`` (immediate synchronous dispatch).  We
# re-export them here so callers can import from a single module without caring
# whether the Rust extension is present.
#
# ``PyPumpedDispatcher`` is the Rust equivalent of :class:`MayaUiDispatcher`
# for *string-payload* dispatch (IPC-style).  For *callable* dispatch —
# required by the in-process executor — :class:`MayaUiDispatcher` must be
# used.  The two dispatchers are complementary, not mutually exclusive.
try:
    from dcc_mcp_core import PyPumpedDispatcher, PyStandaloneDispatcher  # noqa: F401
except ImportError:  # pragma: no cover — core is a hard dep at runtime
    PyPumpedDispatcher = None  # type: ignore[assignment,misc]
    PyStandaloneDispatcher = None  # type: ignore[assignment,misc]

# ── Constants ─────────────────────────────────────────────────────────────────

#: Default time budget (milliseconds) per idle-event pump cycle.
DEFAULT_BUDGET_MS = 8

#: Default soft timeout for individual jobs (milliseconds).
DEFAULT_JOB_TIMEOUT_MS = 30_000

#: Overrun threshold — any pump tick that spends more than ``budget_ms`` × this
#: multiplier counts as an ``overrun_cycles`` in :class:`MayaUiPump.stats`.
#: Matches the wording in issue #85: *"ticks that exceeded ``budget_ms * 2``"*.
OVERRUN_MULTIPLIER = 2.0

# ── Per-job cancellation token (contextvars, issue #85) ──────────────────────

#: Context-local slot pointing to the currently-executing :class:`_JobEntry`.
#: Set by :meth:`MayaUiDispatcher.drain_queue` around :meth:`_JobEntry.execute`
#: so skill scripts running on the UI thread can discover whether the caller
#: has signalled cancellation via :meth:`MayaUiDispatcher.cancel` — even when
#: the script was launched outside an MCP request context (queued batch
#: render, scriptJob, etc.).
_current_job: contextvars.ContextVar[Optional["_JobEntry"]] = contextvars.ContextVar(
    "dcc_mcp_maya_current_job",
    default=None,
)


# ── Job types ─────────────────────────────────────────────────────────────────


class _JobEntry:
    """Internal job wrapper queued for main-thread execution."""

    __slots__ = (
        "request_id",
        "affinity",
        "task",
        "timeout_ms",
        "event",
        "outcome",
        "cancel_flag",
        # Issue #85 — async dispatch linkage fields.
        # ``job_id`` is the opaque identifier from core JobManager (#316);
        # ``None`` for synchronous (blocking) submissions.
        "job_id",
        # ``progress_token`` is echoed from ``_meta.progressToken`` on the
        # MCP request; ``None`` when the client did not request progress.
        "progress_token",
        # ``on_complete`` callback invoked by execute() for async jobs;
        # receives the outcome dict.  ``None`` for synchronous submissions.
        "on_complete",
    )

    def __init__(
        self,
        request_id: str,
        affinity: str,
        task: Callable[[], Any],
        timeout_ms: Optional[int] = None,
        *,
        job_id: Optional[str] = None,
        progress_token: Optional[str] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.request_id = request_id
        self.affinity = affinity
        self.task = task
        self.timeout_ms = timeout_ms or DEFAULT_JOB_TIMEOUT_MS
        self.event = threading.Event()
        self.outcome: Optional[Dict[str, Any]] = None
        # Per-job cancellation flag — set by :meth:`MayaUiDispatcher.cancel`
        # (pre-execute) or :meth:`MayaUiDispatcher.shutdown` (drain). The
        # flag is a plain :class:`threading.Event` rather than a
        # :class:`~dcc_mcp_core.cancellation.CancelToken` so we stay
        # dependency-free for the transport path. See
        # :func:`check_maya_cancelled` for the skill-facing probe.
        self.cancel_flag = threading.Event()
        self.job_id = job_id
        self.progress_token = progress_token
        self.on_complete = on_complete

    def cancel(self) -> None:
        """Signal cooperative cancellation to the task — idempotent.

        Does NOT interrupt a running :meth:`execute`: the task must call
        :func:`check_maya_cancelled` at a safe checkpoint to observe the
        flag and raise :class:`~dcc_mcp_core.cancellation.CancelledError`.
        """
        self.cancel_flag.set()

    @property
    def cancelled(self) -> bool:
        """Whether :meth:`cancel` has been invoked on this job."""
        return self.cancel_flag.is_set()

    def execute(self) -> Dict[str, Any]:
        """Execute the task and populate ``self.outcome``.

        For async jobs (``on_complete`` is set) the completion callback is
        invoked **after** ``self.event`` is fired so callers that poll
        ``event.wait()`` always see the populated outcome before any
        side-effects in the callback.
        """
        token = _current_job.set(self)
        try:
            output = self.task()
            self.outcome = {
                "request_id": self.request_id,
                "affinity": self.affinity,
                "success": True,
                "output": output,
                "error": None,
                "job_id": self.job_id,
            }
        except Exception as exc:
            # :class:`~dcc_mcp_core.cancellation.CancelledError` surfaces
            # through this branch too — the outer caller can distinguish
            # cancellation by checking ``self.cancelled``.
            self.outcome = {
                "request_id": self.request_id,
                "affinity": self.affinity,
                "success": False,
                "output": None,
                "error": str(exc),
                "job_id": self.job_id,
            }
        finally:
            _current_job.reset(token)
        self.event.set()
        if self.on_complete is not None:
            try:
                self.on_complete(self.outcome)
            except Exception as cb_exc:  # pragma: no cover
                logger.warning("_JobEntry.on_complete raised: %s", cb_exc)
        return self.outcome


# ── Cooperative cancellation (issue #85) ─────────────────────────────────────


def check_maya_cancelled() -> None:
    """Raise :class:`~dcc_mcp_core.cancellation.CancelledError` on cancellation.

    Used by skill scripts inside long-running loops so the caller can
    preempt work without Maya's UI thread running unbounded. The helper
    respects **both** cancellation sources:

    1. ``dcc_mcp_core.cancellation.check_cancelled()`` — the MCP request
       context set by the HTTP handler when a ``notifications/cancelled``
       arrives for the owning ``tools/call``.
    2. The per-job :attr:`_JobEntry.cancel_flag`, populated by
       :meth:`MayaUiDispatcher.cancel` / :meth:`MayaUiDispatcher.shutdown`.
       This path covers jobs launched **outside** an MCP request
       (queued batch render, scriptJob, etc.) where the
       contextvar-based core token is not installed.

    When neither source reports cancellation, the call is a cheap no-op.

    Example::

        from dcc_mcp_maya.dispatcher import check_maya_cancelled

        def run(frames):
            for f in frames:
                check_maya_cancelled()        # safe checkpoint
                cmds.currentTime(f)
                cmds.render()

    Raises
    ------
    dcc_mcp_core.cancellation.CancelledError
        When either the MCP request or the owning dispatcher has
        signalled cancellation.
    """
    # Layer 1: honour the core MCP request token if one is installed.
    try:
        from dcc_mcp_core.cancellation import (  # noqa: PLC0415
            CancelledError,
            check_cancelled,
        )
    except ImportError:  # pragma: no cover — core is a hard dep at runtime
        CancelledError = RuntimeError  # type: ignore[assignment]

        def check_cancelled() -> None:  # type: ignore[no-redef]
            return

    check_cancelled()

    # Layer 2: honour the Maya-side per-job flag, if we are inside an
    # :class:`_JobEntry.execute` call.
    job = _current_job.get()
    if job is not None and job.cancelled:
        raise CancelledError("Maya job cancelled by dispatcher")


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
        # Active in-flight jobs (executing on the UI thread). Populated by
        # :meth:`drain_queue` and consulted by :meth:`shutdown` so a stop
        # signal can fire :attr:`_JobEntry.cancel_flag` / ``event`` for
        # jobs that are already running — otherwise their blocked
        # :meth:`submit_callable` caller would hang forever (issue #89).
        self._active: Dict[str, _JobEntry] = {}
        self._shutdown = False

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

    def submit_async_callable(
        self,
        request_id: str,
        task: Callable[[], Any],
        *,
        job_id: Optional[str] = None,
        progress_token: Optional[str] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        affinity: str = "main",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Enqueue a callable for main-thread execution without blocking.

        Unlike :meth:`submit_callable`, this method returns **immediately**
        (typically < 1 ms) with a pending envelope. The actual execution
        happens on Maya's UI thread the next time the pump ticks.

        This is the async dispatch path used by the MCP HTTP server when a
        ``tools/call`` opts into async mode (issue #85 / core #318):

        1. Client sends ``_meta.dcc.async = true``, or
        2. Client sends ``_meta.progressToken``, or
        3. The tool declares ``execution: async`` in ActionMeta.

        Parameters
        ----------
        request_id:
            Unique request identifier (echoed in the return dict and outcome).
        task:
            Zero-argument callable executed on the target thread.
        job_id:
            Opaque identifier from core ``JobManager`` (#316). Included in
            the outcome dict so callers can correlate with ``jobs.get_status``.
        progress_token:
            Echoed from ``_meta.progressToken`` — stored on the entry for
            future ``notifications/progress`` frames.
        on_complete:
            Optional callback invoked with the final outcome dict when the
            task finishes. Called from the UI thread.
        affinity:
            ``"any"`` or ``"main"`` (default ``"main"``).
        timeout_ms:
            Soft timeout in milliseconds (does not block the caller).

        Returns
        -------
        dict
            Pending envelope: ``{"request_id", "job_id", "status": "pending"}``.
        """
        affinity = affinity.lower()

        if self._shutdown:
            return {
                "request_id": request_id,
                "job_id": job_id,
                "status": "interrupted",
                "success": False,
                "error": "Interrupted",
            }

        if affinity == "any":
            # For "any" affinity, run in a background thread immediately.
            def _bg():
                result = self._run_any(request_id, task, affinity)
                result["job_id"] = job_id
                if on_complete is not None:
                    try:
                        on_complete(result)
                    except Exception as exc:  # pragma: no cover
                        logger.warning("submit_async_callable on_complete raised: %s", exc)

            t = threading.Thread(target=_bg, daemon=True, name=f"mcp-async-{request_id}")
            t.start()
        else:
            job = _JobEntry(
                request_id,
                affinity,
                task,
                timeout_ms,
                job_id=job_id,
                progress_token=progress_token,
                on_complete=on_complete,
            )
            with self._lock:
                self._main_queue.append(job)
            self._maybe_poke_deferred()

        return {
            "request_id": request_id,
            "job_id": job_id,
            "status": "pending",
            "success": True,
            "error": None,
        }

    def cancel(self, request_id: str) -> bool:
        """Signal cancellation for a pending or running main-thread job.

        If the job is still queued, it is removed and its outcome is
        populated with ``error="Cancelled"`` before :meth:`execute` ever
        runs. If the job is already executing, the per-job cancel flag
        is set so a cooperating task that calls
        :func:`check_maya_cancelled` at a safe checkpoint can observe the
        request and raise :class:`~dcc_mcp_core.cancellation.CancelledError`.

        Returns
        -------
        bool
            ``True`` when the job was found (queued or running).
        """
        with self._lock:
            self._cancelled.add(request_id)

            # Queued job: short-circuit now, before drain_queue runs it.
            for job in self._main_queue:
                if job.request_id == request_id:
                    job.cancel()
                    job.outcome = {
                        "request_id": request_id,
                        "affinity": job.affinity,
                        "success": False,
                        "output": None,
                        "error": "Cancelled",
                    }
                    job.event.set()
                    return True

            # In-flight job: set the cooperative flag so the task can
            # observe cancellation at its next check_maya_cancelled() call.
            active_job = self._active.get(request_id)
            if active_job is not None:
                active_job.cancel()
                return True

        return False

    def pending_count(self) -> int:
        """Return the number of jobs waiting in the main-thread queue."""
        return len(self._main_queue)

    def shutdown(self, reason: str = "Interrupted") -> int:
        """Drain the dispatcher — mark every pending and in-flight job as ``Interrupted``.

        Called from :meth:`~dcc_mcp_maya.server.MayaMcpServer.stop` (and
        from standalone teardown) so any thread currently blocked inside
        :meth:`submit_callable` / :meth:`submit` unblocks within the
        usual ``event.wait()`` poll instead of hanging forever after
        Maya restarts mid-job. Matches the contract in issue #89:

        * Every queued ``_JobEntry`` gets ``outcome.error=reason`` and
          its :attr:`event` is set so the blocked submitter returns
          immediately on next ``wait()``.
        * Every in-flight job has its :attr:`cancel_flag` set so a
          cooperating task can observe cancellation at its next
          :func:`check_maya_cancelled` checkpoint and exit cleanly.
        * After shutdown, further :meth:`submit_callable` calls return
          the same ``Interrupted`` outcome without enqueuing (so the
          Python thread that tried to submit during teardown does not
          leak). Re-use of a shutdown dispatcher is not supported.

        Returns
        -------
        int
            Total number of queued + in-flight jobs that were signalled.
        """
        signalled = 0
        with self._lock:
            self._shutdown = True

            while self._main_queue:
                job = self._main_queue.popleft()
                job.cancel()
                if job.outcome is None:
                    job.outcome = {
                        "request_id": job.request_id,
                        "affinity": job.affinity,
                        "success": False,
                        "output": None,
                        "error": reason,
                    }
                job.event.set()
                signalled += 1

            for job in list(self._active.values()):
                job.cancel()
                # NOTE: we do NOT set ``job.event`` here — the task is
                # still running on the UI thread. :meth:`execute` will
                # populate ``outcome`` and fire ``event`` when it returns
                # or raises ``CancelledError``. Setting ``event`` now
                # would race with :meth:`execute`.
                signalled += 1

        if signalled:
            logger.info(
                "MayaUiDispatcher.shutdown: signalled %d job(s) with reason=%r",
                signalled,
                reason,
            )
        return signalled

    @property
    def is_shutdown(self) -> bool:
        """``True`` once :meth:`shutdown` has been called."""
        return self._shutdown

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
                # Track in-flight job so shutdown() / cancel() can set
                # the cooperative flag while execute() runs.
                self._active[job.request_id] = job

            try:
                job.execute()
            finally:
                with self._lock:
                    self._active.pop(job.request_id, None)
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
            if self._shutdown:
                # Post-shutdown submissions must not hang — return
                # immediately with the same outcome shape the drain path
                # produces for interrupted jobs (issue #89).
                return {
                    "request_id": request_id,
                    "affinity": affinity,
                    "success": False,
                    "output": None,
                    "error": "Interrupted",
                }
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

    def submit_async_callable(
        self,
        request_id: str,
        task: Callable[[], Any],
        *,
        job_id: Optional[str] = None,
        progress_token: Optional[str] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        affinity: str = "any",
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a callable synchronously and invoke ``on_complete``.

        Standalone mode has no background queue, so this executes immediately
        on the calling thread and returns a completed envelope.  The
        ``on_complete`` callback, if provided, is called before returning.
        """
        result = self.submit_callable(request_id, task, affinity, timeout_ms)
        result["job_id"] = job_id
        result["status"] = "completed" if result.get("success") else "failed"
        if on_complete is not None:
            try:
                on_complete(result)
            except Exception as exc:  # pragma: no cover
                logger.warning("MayaStandaloneDispatcher.submit_async_callable on_complete raised: %s", exc)
        return result

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
        self._stats: Dict[str, float] = {
            "total_executed": 0,
            "total_cycles": 0,
            "total_elapsed_ms": 0.0,
            # Issue #85 §4 — ticks that exceeded ``budget_ms`` × OVERRUN_MULTIPLIER.
            # A non-zero value means ``MayaUiPump`` cannot chunk the work
            # further and the UI thread is being saturated by a single
            # non-cooperative ``cmds.*`` call. Skill authors should move
            # the offending logic behind :func:`check_maya_cancelled`
            # so it yields periodically.
            "overrun_cycles": 0,
            # Worst single-job wall-clock time observed across all cycles.
            # Feeds the ``dcc_maya_job_duration_seconds`` histogram (#87).
            "longest_job_ms": 0.0,
        }

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
        """Idle-event callback: drain pending jobs within the budget.

        Important preemption caveat (issue #85 §4):
        ``drain_queue(budget_ms)`` only checks the deadline **between**
        jobs. When a skill script makes a single, non-cooperative
        ``cmds.*`` call that blocks the UI thread for seconds, this tick
        cannot preempt it — Maya itself has no tool to interrupt a
        running Python callable. The tick will be counted as an
        ``overrun_cycles`` so operators can tell the difference between
        "the pump is tuned too aggressively" and "a skill needs to be
        chunked behind :func:`check_maya_cancelled`".
        """
        start = time.monotonic()
        executed, remaining = self._dispatcher.drain_queue(self._budget_ms)

        elapsed_ms = (time.monotonic() - start) * 1000.0
        self._stats["total_executed"] += executed
        self._stats["total_cycles"] += 1
        self._stats["total_elapsed_ms"] += elapsed_ms

        # Overrun bookkeeping — see OVERRUN_MULTIPLIER.
        if elapsed_ms > self._budget_ms * OVERRUN_MULTIPLIER:
            self._stats["overrun_cycles"] += 1

        # ``longest_job_ms`` approximates the worst single-job duration.
        # ``drain_queue`` may execute multiple jobs per tick when each
        # finishes inside the budget; in that case the per-job worst is
        # bounded by ``elapsed_ms / max(executed, 1)``. When a single
        # job blows past the budget it dominates the tick, which is
        # exactly the case we want this metric to catch, so use the
        # larger of the two estimates.
        if executed > 0:
            avg_job_ms = elapsed_ms / executed
            worst_job_ms = elapsed_ms if executed == 1 else max(elapsed_ms, avg_job_ms)
            if worst_job_ms > self._stats["longest_job_ms"]:
                self._stats["longest_job_ms"] = worst_job_ms

        if remaining > 0:
            # Re-poke Maya so we get another idle event quickly
            try:
                import maya.cmds as cmds  # noqa: PLC0415

                cmds.refresh(force=True)
            except Exception:
                pass


# ── Factory helpers ───────────────────────────────────────────────────────────


def create_dispatcher(
    budget_ms: float = DEFAULT_BUDGET_MS,
) -> Tuple[Any, Optional[MayaUiPump]]:
    """Create the appropriate dispatcher for the current Maya environment.

    Returns a ``(dispatcher, pump)`` pair where *dispatcher* is a
    :class:`MayaUiDispatcher` (interactive) or
    :class:`MayaStandaloneDispatcher` (batch / ``mayapy``), and *pump* is a
    :class:`MayaUiPump` or ``None`` respectively.

    The returned :class:`MayaUiDispatcher` supports ``submit_callable`` for
    routing arbitrary Python callables to Maya's UI thread — required by the
    in-process skill executor.  Use :func:`create_pumped_dispatcher` when
    you want the Rust-backed :class:`PyPumpedDispatcher` (string-payload
    dispatch only) instead.

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


def create_pumped_dispatcher(
    budget_ms: float = DEFAULT_BUDGET_MS,
) -> Tuple[Any, Optional["_CorePump"]]:
    """Create a Rust-backed :class:`PyPumpedDispatcher` for the current Maya environment.

    This is an alternative to :func:`create_dispatcher` that returns the
    core's ``PyPumpedDispatcher`` instead of :class:`MayaUiDispatcher`.
    Use it when you need IPC-style string-payload dispatch routed through
    the Rust main-thread pump.

    .. note::
        ``PyPumpedDispatcher`` only supports ``submit(action_name, payload,
        affinity)`` where *payload* is a string.  It cannot dispatch arbitrary
        Python callables.  For in-process skill execution, the
        :class:`MayaUiDispatcher` returned by :func:`create_dispatcher` must
        be used.

    Returns
    -------
    tuple[PyPumpedDispatcher | MayaStandaloneDispatcher, _CorePump | None]
        A ``(dispatcher, pump)`` pair.  Returns
        ``(MayaStandaloneDispatcher(), None)`` when not inside an interactive
        Maya session or when ``PyPumpedDispatcher`` is not available.
    """
    if PyPumpedDispatcher is None:
        logger.warning("PyPumpedDispatcher not available — falling back to MayaStandaloneDispatcher")
        return MayaStandaloneDispatcher(), None

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        is_batch = cmds.about(batch=True)
    except ImportError:
        is_batch = True

    if is_batch:
        return MayaStandaloneDispatcher(), None

    core_dispatcher = PyPumpedDispatcher(budget_ms=int(budget_ms))
    pump = _CorePump(core_dispatcher, budget_ms=budget_ms)
    return core_dispatcher, pump


class _CorePump:
    """Idle-event pump adapter for :class:`PyPumpedDispatcher`.

    Wraps :class:`PyPumpedDispatcher` in the same scriptJob-based idle hook
    that :class:`MayaUiPump` uses for :class:`MayaUiDispatcher`, so callers
    can treat both pump types identically (``install()`` / ``uninstall()``).

    Parameters
    ----------
    dispatcher:
        A :class:`PyPumpedDispatcher` instance whose :meth:`pump` method
        should be called on each idle tick.
    budget_ms:
        Maximum milliseconds for each pump call.  Passed to
        :meth:`PyPumpedDispatcher.pump_with_budget`.
    """

    def __init__(self, dispatcher: Any, budget_ms: float = DEFAULT_BUDGET_MS) -> None:
        self._dispatcher = dispatcher
        self._budget_ms = budget_ms
        self._script_job_id: Optional[int] = None
        self._installed = False

    @property
    def is_installed(self) -> bool:
        """``True`` if the idle scriptJob is currently active."""
        return self._installed

    def install(self) -> bool:
        """Register the idle-event scriptJob with Maya."""
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
                "_CorePump installed (scriptJob=%d, budget=%.1f ms)",
                self._script_job_id,
                self._budget_ms,
            )
            return True
        except ImportError:
            logger.warning("_CorePump: maya.cmds not available — install skipped")
            return False
        except Exception as exc:
            logger.error("_CorePump: failed to install scriptJob: %s", exc)
            return False

    def uninstall(self) -> None:
        """Remove the idle-event scriptJob from Maya."""
        if not self._installed:
            return
        try:
            import maya.cmds as cmds  # noqa: PLC0415

            if self._script_job_id is not None:
                cmds.scriptJob(kill=self._script_job_id, force=True)
                logger.info("_CorePump uninstalled (scriptJob=%d)", self._script_job_id)
        except Exception as exc:
            logger.warning("_CorePump: error removing scriptJob: %s", exc)
        finally:
            self._script_job_id = None
            self._installed = False

    def _pump_tick(self) -> None:
        """Idle-event callback — drain pending Rust-side main-thread jobs."""
        try:
            stats = self._dispatcher.pump_with_budget(int(self._budget_ms))
            remaining = stats.get("remaining", 0) if isinstance(stats, dict) else 0
            if remaining > 0:
                try:
                    import maya.cmds as cmds  # noqa: PLC0415

                    cmds.refresh(force=True)
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("_CorePump._pump_tick error: %s", exc)
