"""Out-of-process sidecar integration for dcc-mcp-maya (RFC #998).

This sub-package wires Maya's plugin into the `dcc-mcp-server sidecar`
binary that ships from `dcc-mcp-core` (see PRs loonghao/dcc-mcp-core#1003,
#1005). The sidecar runs as a **separate OS process**, supervised by the
Maya plugin's PID, and survives Maya's C++ aborts / Qt-modal crashes /
non-cooperative shutdowns. When the DCC dies it surfaces a structured
`host-died` envelope to the gateway instead of cascading transport
errors.

## Activation

Sidecar mode is **opt-in** and **does not replace** the existing
in-process MCP HTTP server. Operators enable it by:

1. Setting the environment variable ``DCC_MCP_MAYA_SIDECAR=1``
   before launching Maya.
2. Loading the dedicated Maya plug-in
   ``dcc_mcp_maya_sidecar_plugin`` (a separate plug-in from
   the default ``dcc_mcp_maya_plugin``).

When both conditions are met, plug-in load opens a Maya ``commandPort``
on a free TCP port and spawns the sidecar binary with
``--host-rpc commandport://...`` plus ``--watch-pid <maya pid>``. When
Maya exits (cleanly or via crash) the sidecar's PPID-watch loop
terminates it, and the OS-held FileRegistry sentinel lock is released.

## Why opt-in

The default in-process path remains the lowest-latency route for the
vast majority of skill actions (cheap reads, pure-Python ops). Sidecar
mode is reserved for actions tagged ``risk_class: high-crash`` in
``tools.yaml`` once the gateway router in ``dcc-mcp-core`` learns to
honour the field (Phase 2 of #998). Until that wiring lands, this
package exercises the **lifecycle** half of the contract: spawn,
register, supervise, deregister.

## Public surface

* :func:`start_sidecar` — open commandPort, spawn the sidecar
  subprocess, return a :class:`SidecarHandle`.
* :func:`stop_sidecar` — terminate the sidecar and close the commandPort.
* :func:`is_sidecar_mode_enabled` — read the env-var gate.
* :class:`SidecarHandle` — lifetime handle exposing
  ``proc`` (``subprocess.Popen``), ``command_port`` (``int``),
  ``host_rpc_uri`` (``str``), ``binary_path`` (``Path``).
* :class:`SidecarSpawnError` — raised on resolver / port-allocation
  failure.

The plug-in entry point (`maya/plugin/dcc_mcp_maya_sidecar_plugin.py`)
is intentionally thin — all real logic lives here so unit tests can
exercise the lifecycle without loading Maya.
"""

from __future__ import annotations

from dcc_mcp_maya.sidecar._commandport import (
    DEFAULT_COMMAND_PORT_HINT,
    allocate_free_port,
    build_host_rpc_uri,
)
from dcc_mcp_maya.sidecar._dispatcher import dispatch, dispatch_payload
from dcc_mcp_maya.sidecar._resolver import (
    ENV_SIDECAR_BINARY,
    SidecarBinaryError,
    resolve_sidecar_binary,
)
from dcc_mcp_maya.sidecar._supervisor import (
    ENV_SIDECAR_MODE,
    SidecarHandle,
    SidecarSpawnError,
    is_sidecar_mode_enabled,
    start_sidecar,
    stop_sidecar,
)

__all__ = [
    "DEFAULT_COMMAND_PORT_HINT",
    "ENV_SIDECAR_BINARY",
    "ENV_SIDECAR_MODE",
    "SidecarBinaryError",
    "SidecarHandle",
    "SidecarSpawnError",
    "allocate_free_port",
    "build_host_rpc_uri",
    "dispatch",
    "dispatch_payload",
    "is_sidecar_mode_enabled",
    "resolve_sidecar_binary",
    "start_sidecar",
    "stop_sidecar",
]
