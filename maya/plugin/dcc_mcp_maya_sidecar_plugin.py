"""dcc_mcp_maya_sidecar_plugin — opt-in out-of-process sidecar entry.

This plug-in is **separate** from the default ``dcc_mcp_maya_plugin``
and exists solely to wire the experimental sidecar workflow described
in RFC #998 (see loonghao/dcc-mcp-core#998, #1002, #1003, #1005). It is
loaded **in addition** to the default plug-in, not as a replacement —
the in-process MCP HTTP server keeps running and continues to serve
every low-risk skill action with the existing latency profile. Sidecar
mode only matters for actions tagged ``risk_class: high-crash`` once
the gateway router learns to honour the field (Phase 2 of #998).

Activation
==========

Sidecar mode is **off by default**. Operators turn it on by setting::

    DCC_MCP_MAYA_SIDECAR=1

before launching Maya, then loading this plug-in via
``cmds.loadPlugin("dcc_mcp_maya_sidecar_plugin")`` or the Plug-in
Manager UI. The plug-in is intentionally short so it stays auditable
at a glance — all real logic lives in :mod:`dcc_mcp_maya.sidecar`.

Lifecycle
=========

* ``initializePlugin`` — when sidecar mode is enabled, schedule
  :func:`_start` via ``cmds.evalDeferred(..., lowestPriority=True)``
  so it runs after Maya's main-thread boot drains. ``_start`` opens
  ``commandPort`` on a free TCP port and spawns
  ``dcc-mcp-server sidecar``.

* ``uninitializePlugin`` — terminate the sidecar subprocess and close
  ``commandPort``. Best-effort; never raises.

The plug-in is a no-op when ``DCC_MCP_MAYA_SIDECAR`` is unset. That
keeps it safe to load by default in user setups that want to ship the
.mod file but only activate the workflow via env var per session.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import maya.api.OpenMaya as om  # Python API 2.0
import maya.cmds as cmds

logger = logging.getLogger(__name__)

VENDOR = "dcc-mcp"


# ── ensure dcc_mcp_maya is importable ────────────────────────────────────


def _ensure_package_importable() -> None:
    """Locate the sibling ``python/`` tree and put it on ``sys.path``.

    Mirrors the resolution used by the default plug-in so the two can
    be installed under the same .mod file structure.
    """
    try:
        return Path(__file__).resolve().parent
    except NameError:
        pass

    try:
        import dcc_mcp_maya  # noqa: F401
        return
    except ImportError:
        pass

    plugin_dir = Path(sys._getframe(0).f_code.co_filename).resolve().parent
    module_root = plugin_dir.parent
    python_dir = module_root / (
        "python37" if sys.version_info[:2] == (3, 7) else "python"
    )
    if not python_dir.is_dir():
        python_dir = module_root / "python"
    if python_dir.is_dir():
        python_str = str(python_dir.resolve())
        if python_str not in sys.path:
            sys.path.insert(0, python_str)


_ensure_package_importable()


def _get_version() -> str:
    try:
        from dcc_mcp_maya.__version__ import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "0.0.0"


VERSION = _get_version()


# ── module state ─────────────────────────────────────────────────────────

_handle = None  # type: ignore[assignment]


# ── plug-in API ──────────────────────────────────────────────────────────


def maya_useNewAPI() -> None:
    """Declare Python API 2.0 to Maya."""


def initializePlugin(plugin):
    """Called by Maya when the plug-in is loaded."""
    om.MFnPlugin(plugin, VENDOR, VERSION)

    from dcc_mcp_maya.sidecar import is_sidecar_mode_enabled

    if not is_sidecar_mode_enabled():
        logger.info(
            "dcc-mcp-maya-sidecar plug-in loaded but DCC_MCP_MAYA_SIDECAR is "
            "not set — sidecar will not start. This is the default."
        )
        return

    try:
        cmds.evalDeferred(_start, lowestPriority=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("dcc-mcp-maya-sidecar: failed to schedule startup: %s", exc)
        raise RuntimeError(f"dcc-mcp-maya-sidecar init failed: {exc}") from exc


def uninitializePlugin(plugin):
    """Called by Maya when the plug-in is unloaded."""
    om.MFnPlugin(plugin)

    global _handle
    if _handle is None:
        return

    try:
        from dcc_mcp_maya.sidecar import stop_sidecar

        stop_sidecar(_handle)
    except Exception as exc:  # noqa: BLE001
        logger.warning("dcc-mcp-maya-sidecar: stop_sidecar raised: %s", exc)
    finally:
        _handle = None


# ── private startup path ─────────────────────────────────────────────────


def _start() -> None:
    """Open commandPort and spawn the sidecar binary.

    Runs on the Maya main thread after the UI is idle — see the
    ``evalDeferred(lowestPriority=True)`` rationale in the default
    plug-in's ``_start_async`` docstring. The same rationale applies
    here: cross-thread hand-off during plugin init is unreliable on
    Maya 2022/2023, so we just wait for Maya to be ready then run
    synchronously.
    """
    global _handle
    try:
        from dcc_mcp_maya.sidecar import SidecarSpawnError, start_sidecar
    except ImportError as exc:
        logger.error("dcc-mcp-maya-sidecar: package import failed: %s", exc)
        return

    try:
        _handle = start_sidecar()
    except SidecarSpawnError as exc:
        logger.error("dcc-mcp-maya-sidecar: start failed: %s", exc)
        _handle = None
        return

    _print_startup_banner(_handle)


def _print_startup_banner(handle) -> None:  # noqa: ANN001 — module-level type avoidance
    border = "=" * 60
    lines = [
        border,
        f"  dcc-mcp-maya-sidecar v{VERSION}",
        border,
        f"  Binary       : {handle.binary_path}",
        f"  PID          : {handle.proc.pid}",
        f"  commandPort  : :{handle.command_port}",
        f"  host-rpc URI : {handle.host_rpc_uri}",
        f"  watch-pid    : {handle.maya_pid} (Maya)",
        border,
    ]
    banner = "\n".join(lines)
    print(banner)  # noqa: T201 — intentional console output

    try:
        cmds.inViewMessage(
            amg=f"DCC MCP sidecar PID <b>{handle.proc.pid}</b> attached",
            pos="topCenter",
            fade=True,
            fadeStayTime=4000,
        )
    except Exception:  # noqa: BLE001 — viewport HUD is cosmetic
        pass
