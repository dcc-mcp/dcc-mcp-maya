"""Drop-in ``userSetup.py`` for running multiple Maya instances side by side.

Place this file in your Maya ``scripts/`` directory (or ``source`` it from
your existing ``userSetup.py``).  On every Maya launch it:

1. Leaves the MCP instance port unset so dcc-mcp-core binds port ``0`` and the
   operating system assigns a free port without a probe/bind race.
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
from typing import Optional

logger = logging.getLogger(__name__)


# ── Tunables ──────────────────────────────────────────────────────────────────

#: Gateway port shared by every instance on this host.  The first Maya to
#: bind it becomes the gateway; the rest register as backends.
DEFAULT_GATEWAY_PORT: int = 9765


# ── Environment plumbing ──────────────────────────────────────────────────────


def apply_multi_instance_env(
    gateway_port: int = DEFAULT_GATEWAY_PORT,
    dcc_pid: Optional[int] = None,
) -> None:
    """Populate the dcc-mcp-maya env vars for a multi-instance deployment.

    Idempotent — values the operator already set (e.g. via a launcher wrapper)
    are preserved via ``setdefault``. ``DCC_MCP_MAYA_PORT`` is deliberately
    untouched: core resolves an explicit operator override, otherwise binds
    port ``0`` directly and publishes the exact bound URL.
    """
    os.environ.setdefault("DCC_MCP_GATEWAY_PORT", str(gateway_port))
    os.environ.setdefault("DCC_MCP_MAYA_DCC_PID", str(dcc_pid if dcc_pid is not None else os.getpid()))


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
                "dcc-mcp-maya loaded (pid=%s, gateway=%s, instance port=%s)",
                os.environ.get("DCC_MCP_MAYA_DCC_PID"),
                os.environ.get("DCC_MCP_GATEWAY_PORT"),
                os.environ.get("DCC_MCP_MAYA_PORT", "OS-assigned"),
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
