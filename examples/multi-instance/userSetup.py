"""Drop-in ``userSetup.py`` for running multiple Maya instances side by side.

Place this file in your Maya ``scripts/`` directory (or ``source`` it from
your existing ``userSetup.py``).  On every Maya launch it:

1. Picks the first free port from :data:`PORT_RANGE` (falls back to an
   OS-assigned port if every slot is busy).
2. Sets ``DCC_MCP_MAYA_DCC_PID`` to ``os.getpid()`` so ``diagnostics__*``
   tools route to the correct instance.
3. Enables the shared MCP gateway on :data:`DEFAULT_GATEWAY_PORT` — the
   first Maya to bind that port wins the election.
4. Loads the ``dcc_mcp_maya`` plugin via :mod:`maya.utils.executeDeferred`.

See ``docs/guide/multi-instance.md`` (EN) / ``docs/zh/guide/multi-instance.md``
(ZH) for the full deployment guide.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import socket
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


# ── Tunables ──────────────────────────────────────────────────────────────────

#: Reserved HTTP port range for Maya MCP servers on this workstation.
#:
#: Every Maya instance picks the first free slot from this range.  Keep the
#: range wide enough to cover the maximum number of concurrent Maya sessions
#: you expect on a single box.  Ports outside this range are left for other
#: applications.
PORT_RANGE: range = range(8765, 8776)

#: Gateway port shared by every instance on this host.  The first Maya to
#: bind it becomes the gateway; the rest register as backends.
DEFAULT_GATEWAY_PORT: int = 9765


# ── Port selection ────────────────────────────────────────────────────────────


def _port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    """Return ``True`` when *port* on *host* can be bound right now."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def pick_free_port(candidates: Iterable[int]) -> int:
    """Return the first port in *candidates* that is currently free.

    Falls back to ``0`` (OS-assigned ephemeral port) when every candidate
    is busy.  A return value of ``0`` is passed verbatim to the MCP
    server; ``McpHttpServer`` accepts ``0`` and binds whatever port the
    OS hands out.
    """
    for port in candidates:
        if _port_is_free(port):
            return port
    return 0


# ── Environment plumbing ──────────────────────────────────────────────────────


def apply_multi_instance_env(
    port_range: Iterable[int] = PORT_RANGE,
    gateway_port: int = DEFAULT_GATEWAY_PORT,
    dcc_pid: Optional[int] = None,
) -> None:
    """Populate the dcc-mcp-maya env vars for a multi-instance deployment.

    Idempotent — values the operator already set (e.g. via a launcher
    wrapper) are preserved via ``setdefault``.  Only ``DCC_MCP_MAYA_PORT``
    is unconditionally re-computed on each call, because the previously
    reserved port may no longer be free by the time Maya actually starts.
    """
    os.environ.setdefault("DCC_MCP_GATEWAY_PORT", str(gateway_port))
    os.environ.setdefault("DCC_MCP_MAYA_DCC_PID", str(dcc_pid if dcc_pid is not None else os.getpid()))
    os.environ["DCC_MCP_MAYA_PORT"] = str(pick_free_port(port_range))


# ── Plugin loader ─────────────────────────────────────────────────────────────


def _load_dcc_mcp_maya() -> None:
    """Apply env defaults and load the ``dcc_mcp_maya`` Maya plugin."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return

    apply_multi_instance_env()

    try:
        if not cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
            cmds.loadPlugin("dcc_mcp_maya_plugin", quiet=True)
            logger.info(
                "dcc-mcp-maya loaded on port %s (pid=%s, gateway=%s)",
                os.environ.get("DCC_MCP_MAYA_PORT"),
                os.environ.get("DCC_MCP_MAYA_DCC_PID"),
                os.environ.get("DCC_MCP_GATEWAY_PORT"),
            )
    except Exception as exc:  # pragma: no cover  -- defensive, Maya only
        logger.warning("dcc-mcp-maya plugin load failed: %s", exc)


try:
    import maya.utils  # type: ignore[import]

    maya.utils.executeDeferred(_load_dcc_mcp_maya)
except ImportError:
    # Not running inside Maya — the helpers above are still importable for
    # testing / introspection (see tests/test_multi_instance_example.py).
    pass
