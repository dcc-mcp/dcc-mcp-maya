"""Maya thread-affinity dispatchers (issue #128 directory module).

Public API surface preserved 1:1 with the previous single-file
``dispatcher.py``: every symbol documented in :pep:`8`-compliant
``__all__`` below remains importable from
``dcc_mcp_maya.dispatcher``.

The implementation is split per Single Responsibility into:

================  ====================================================
Module            Purpose
================  ====================================================
``job``           ``_JobEntry`` + ``_current_job`` ContextVar
``cancel``        ``check_maya_cancelled`` cooperative checkpoint
``ui``            ``MayaUiDispatcher`` (interactive)
``standalone``    ``MayaStandaloneDispatcher`` (mayapy / batch)
``pump``          ``MayaUiPump`` / ``_CorePump`` + factory helpers
================  ====================================================

This re-export layer is **zero-overhead**: every name binds to the same
object as the originating submodule.  External callers do not need to
update their imports.

See: https://github.com/loonghao/dcc-mcp-maya/issues/128
"""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.dispatcher.cancel import check_maya_cancelled
from dcc_mcp_maya.dispatcher.job import DEFAULT_JOB_TIMEOUT_MS, _current_job, _JobEntry
from dcc_mcp_maya.dispatcher.pump import (
    DEFAULT_BUDGET_MS,
    OVERRUN_MULTIPLIER,
    MayaUiPump,
    PyPumpedDispatcher,
    PyStandaloneDispatcher,
    _CorePump,
    create_dispatcher,
    create_pumped_dispatcher,
)
from dcc_mcp_maya.dispatcher.standalone import MayaStandaloneDispatcher
from dcc_mcp_maya.dispatcher.ui import MayaUiDispatcher

__all__ = [
    # Cancellation
    "check_maya_cancelled",
    # Constants
    "DEFAULT_BUDGET_MS",
    "DEFAULT_JOB_TIMEOUT_MS",
    "OVERRUN_MULTIPLIER",
    # Dispatchers
    "MayaUiDispatcher",
    "MayaStandaloneDispatcher",
    # Pumps
    "MayaUiPump",
    # Factories
    "create_dispatcher",
    "create_pumped_dispatcher",
    # Core re-exports
    "PyPumpedDispatcher",
    "PyStandaloneDispatcher",
    # Internals exposed for compatibility / advanced use
    "_CorePump",
    "_JobEntry",
    "_current_job",
]
