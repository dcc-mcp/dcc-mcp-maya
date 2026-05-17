"""Cooperative cancellation checkpoint for Maya skill scripts.

Delegates to :func:`dcc_mcp_core.cancellation.check_dcc_cancelled`, which
honours both the MCP cancel token and the per-job handle published by
:class:`~dcc_mcp_core.HostUiDispatcherBase` during job execution.
"""

from __future__ import annotations

from dcc_mcp_core.cancellation import CancelledError, check_dcc_cancelled

__all__ = ["CancelledError", "check_maya_cancelled"]


def check_maya_cancelled() -> None:
    """Raise :class:`~dcc_mcp_core.cancellation.CancelledError` on cancellation."""
    check_dcc_cancelled()
