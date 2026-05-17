"""Maya dispatcher job model — re-exports core :class:`HostUiJobEntry`.

The canonical implementation lives in ``dcc_mcp_core._server.host_ui_dispatcher``
so Blender, Houdini, and other adapters share one job/cancel protocol.
"""

from __future__ import annotations

from dcc_mcp_core import (
    DEFAULT_UI_JOB_TIMEOUT_MS,
    HostUiJobEntry,
    current_host_ui_job,
)

# Legacy private names kept for tests and advanced callers (issue #128).
DEFAULT_JOB_TIMEOUT_MS = DEFAULT_UI_JOB_TIMEOUT_MS
_JobEntry = HostUiJobEntry
_current_job = current_host_ui_job

__all__ = [
    "DEFAULT_JOB_TIMEOUT_MS",
    "_JobEntry",
    "_current_job",
]
