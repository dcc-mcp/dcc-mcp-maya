"""Out-of-process sidecar integration for dcc-mcp-maya (RFC #998).

This sub-package wires Maya's plug-in into the ``dcc-mcp-server sidecar``
binary that ships from ``dcc-mcp-core`` (see PRs loonghao/dcc-mcp-core#1003,
#1005, #1010, #1012). The sidecar runs as a **separate OS process**,
supervised by the Maya plug-in's PID, and survives Maya's C++ aborts /
Qt-modal crashes / non-cooperative shutdowns. When the DCC dies it
surfaces a structured ``host-died`` envelope to the gateway instead of
cascading transport errors.

## Wire format — ``qtserver://`` (RFC #998 Addendum B item 2)

The sidecar binary talks to Maya over the universal Qt-event-loop JSON-line
dispatcher provided by :mod:`dcc_mcp_core.qt_dispatcher`. The dispatcher
binds an ephemeral TCP port via ``QTcpServer`` and runs cooperatively on
Maya's own Qt event loop — structurally immune to the single-flight /
modal-dialog / PyO3-tokio contention failure modes the legacy
``commandPort`` path suffered from (see #1009).

The plug-in flow:

1. Plug-in load → :func:`start_sidecar` eagerly starts the in-Maya Qt
   server on an ephemeral port.
2. The Qt server receives a ``dispatch`` method handler that forwards to
   :mod:`dcc_mcp_maya.sidecar._dispatcher.dispatch_payload` —
   same action-lookup contract as the in-process path.
3. The supervisor spawns ``dcc-mcp-server sidecar --host-rpc
   qtserver://127.0.0.1:<port>`` and the sidecar binary connects back
   to Maya over the JSON-line wire.

No ``commandPort`` is opened on the Maya side.

## Activation

Sidecar mode is enabled by default and does not replace the in-process
MCP HTTP server. Operators can disable it by setting
``DCC_MCP_MAYA_SIDECAR=0`` before launching Maya. The default plug-in
(``dcc_mcp_maya_plugin``) reads the env var inside ``_post_start`` and
spawns the supervisor automatically unless disabled.

## Public surface

* :func:`start_sidecar` — start the in-Maya Qt server, spawn the sidecar
  subprocess, return a :class:`SidecarHandle`.
* :func:`stop_sidecar` — terminate the subprocess and stop the Qt server.
* :func:`build_qtserver_uri` — format the ``qtserver://`` URI the sidecar
  dials. Kept public so tests assert on the wire format from one
  authoritative place.
* :func:`is_sidecar_mode_enabled` — read the env-var gate.
* :class:`SidecarHandle` — lifetime handle exposing ``proc``,
  ``qt_port``, ``qt_binding``, ``host_rpc_uri``, ``binary_path``,
  ``maya_pid``.
* :class:`SidecarSpawnError` — raised on resolver / Qt-start /
  spawn failure.
* :func:`dispatch_payload` — Maya-side wire-frame handler used by the
  in-Maya Qt server's ``dispatch`` method.
"""

from __future__ import annotations

from dcc_mcp_maya.sidecar._dispatcher import dispatch_payload
from dcc_mcp_maya.sidecar._resolver import (
    ENV_SIDECAR_BINARY,
    SidecarBinaryError,
    resolve_sidecar_binary,
)
from dcc_mcp_maya.sidecar._supervisor import (
    DEFAULT_GATEWAY_REMOTE_HOST,
    DEFAULT_GATEWAY_REMOTE_PORT,
    ENV_GATEWAY_NAME,
    ENV_GATEWAY_REMOTE_HOST,
    ENV_GATEWAY_REMOTE_PORT,
    ENV_SIDECAR_MODE,
    SidecarHandle,
    SidecarSpawnError,
    build_qtserver_uri,
    is_sidecar_mode_enabled,
    resolve_gateway_remote_options,
    start_sidecar,
    stop_sidecar,
)

__all__ = [
    "DEFAULT_GATEWAY_REMOTE_HOST",
    "DEFAULT_GATEWAY_REMOTE_PORT",
    "ENV_GATEWAY_NAME",
    "ENV_GATEWAY_REMOTE_HOST",
    "ENV_GATEWAY_REMOTE_PORT",
    "ENV_SIDECAR_BINARY",
    "ENV_SIDECAR_MODE",
    "SidecarBinaryError",
    "SidecarHandle",
    "SidecarSpawnError",
    "build_qtserver_uri",
    "dispatch_payload",
    "is_sidecar_mode_enabled",
    "resolve_sidecar_binary",
    "resolve_gateway_remote_options",
    "start_sidecar",
    "stop_sidecar",
]
