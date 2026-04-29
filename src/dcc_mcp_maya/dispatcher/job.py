"""Internal job model and per-job cancellation context.

Houses the ``_JobEntry`` wrapper and the ``_current_job`` ContextVar that
links the executing job back to :func:`check_maya_cancelled` so skill
scripts can poll the per-job cancellation flag at safe checkpoints.

See: https://github.com/loonghao/dcc-mcp-maya/issues/128
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import contextvars
import logging
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

#: Default soft timeout for individual jobs (milliseconds).
DEFAULT_JOB_TIMEOUT_MS = 30_000

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
