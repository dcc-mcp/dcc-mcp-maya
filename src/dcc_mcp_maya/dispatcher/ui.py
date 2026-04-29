"""Interactive Maya UI-thread dispatcher.

Hosts :class:`MayaUiDispatcher`, the affinity-aware queue used by the
in-process executor when running inside an interactive Maya session
(``Main``-affinity work is funnelled to the UI thread by the
:class:`~dcc_mcp_maya.dispatcher.pump.MayaUiPump`; ``Any``-affinity work
runs immediately on the calling thread).

See: https://github.com/loonghao/dcc-mcp-maya/issues/66,
https://github.com/loonghao/dcc-mcp-maya/issues/128
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

# Import local modules
from dcc_mcp_maya.dispatcher.job import DEFAULT_JOB_TIMEOUT_MS, _JobEntry

logger = logging.getLogger(__name__)


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
