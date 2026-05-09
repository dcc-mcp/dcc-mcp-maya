"""Cooperative cancellation checkpoint for Maya skill scripts.

Provides :func:`check_maya_cancelled`, a dependency-light probe that
honours both the MCP request-bound cancellation token (from
``dcc_mcp_core.cancellation``) and the per-job flag set by
:meth:`MayaUiDispatcher.cancel` / :meth:`MayaUiDispatcher.shutdown`.

See: https://github.com/loonghao/dcc-mcp-maya/issues/85,
https://github.com/loonghao/dcc-mcp-maya/issues/128
"""

# Import future modules
from __future__ import annotations

# Import third-party modules
from dcc_mcp_core.cancellation import CancelledError, check_dcc_cancelled

# Import local modules
from dcc_mcp_maya.dispatcher.job import _current_job


def check_maya_cancelled() -> None:
    """Raise :class:`~dcc_mcp_core.cancellation.CancelledError` on cancellation.

    Used by skill scripts inside long-running loops so the caller can
    preempt work without Maya's UI thread running unbounded. The helper
    respects **both** cancellation sources:

    1. ``dcc_mcp_core.cancellation.check_dcc_cancelled()`` — the MCP request
       token plus any current core job handle.
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
    # Layer 1: honour the core MCP request token and current core job handle.
    check_dcc_cancelled()

    # Layer 2: honour the Maya-side per-job flag, if we are inside an
    # :class:`_JobEntry.execute` call.
    job = _current_job.get()
    if job is not None and job.cancelled:
        raise CancelledError("Maya job cancelled by dispatcher")
