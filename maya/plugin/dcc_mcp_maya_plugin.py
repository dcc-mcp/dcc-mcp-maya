"""dcc_mcp_maya_plugin — Maya plugin entry point.

Loads the MCP Streamable HTTP server inside Maya.

**Plugin file naming**: This file is intentionally named ``dcc_mcp_maya_plugin.py``
(not ``dcc_mcp_maya.py``) to avoid a Python namespace collision.  Maya adds the
``plug-ins/`` directory to ``sys.path``, so a file named ``dcc_mcp_maya.py``
would shadow the ``dcc_mcp_maya`` Python package, breaking all imports inside
the plugin itself.

Installation
------------
Copy this file (or create a symlink) into a directory on ``MAYA_PLUG_IN_PATH``.
Load it via **Window > Settings/Preferences > Plug-in Manager**.

Alternatively, add to ``userSetup.py``::

    import maya.cmds as cmds
    cmds.loadPlugin("dcc_mcp_maya_plugin")

Standalone / batch mode
-----------------------
The plugin is fully usable in ``mayapy`` / Maya standalone.  Menu creation is
skipped automatically when ``MayaWindow`` is not available (i.e. non-interactive
sessions).

Gateway mode (default ON)
-------------------------
By default the plugin joins the auto-gateway on port ``9765``.  The first Maya
instance to start becomes the **gateway**; subsequent instances register as plain
DCC instances.  Both expose their own full MCP tool set.

Connect your MCP client (Claude Desktop, etc.) to the **single gateway endpoint**::

    http://127.0.0.1:9765/mcp

The gateway exposes three discovery meta-tools:
  - ``list_dcc_instances`` — show all running Maya instances
  - ``connect_to_dcc``     — get the direct URL for a specific instance
  - ``get_dcc_instance``   — query a specific instance by id or scene

To **disable** the gateway: set ``DCC_MCP_GATEWAY_PORT=0`` before starting Maya.

Configuration
-------------
``DCC_MCP_MAYA_PORT``
    TCP port for this instance's MCP HTTP server.  Default ``0`` (OS-assigned).
    Using ``0`` is recommended when running multiple Maya instances.

``DCC_MCP_MAYA_SERVER_NAME``
    Name advertised in the MCP ``initialize`` response.  Default: ``"maya-mcp"``.

``DCC_MCP_GATEWAY_PORT``
    Gateway competition port.  Default ``9765``.  Set to ``0`` to disable.

``DCC_MCP_REGISTRY_DIR``
    Directory for the shared ``FileRegistry`` JSON.  Defaults to OS temp dir.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
import sys
import threading
from pathlib import Path

import maya.api.OpenMaya as om  # Python API 2.0 — required for MFnPlugin on Maya 2022-2025
import maya.cmds as cmds

logger = logging.getLogger(__name__)

VENDOR = "dcc-mcp"

# Default gateway port — same as dcc-mcp-server binary default
_DEFAULT_GATEWAY_PORT = 9765


# ── ensure dcc_mcp_maya package is importable ────────────────────────────────


def _ensure_package_importable() -> None:
    """Add the module's python/ directory to sys.path if needed."""
    try:
        import dcc_mcp_maya  # noqa: F401 — already importable, nothing to do

        return
    except ImportError:
        pass

    plugin_dir = Path(__file__).resolve().parent
    module_root = plugin_dir.parent

    maya_version = cmds.about(version=True)
    try:
        major = int(str(maya_version).split(".")[0])
    except (ValueError, IndexError):
        major = 2025

    python_dir = module_root / "python37" if major == 2022 else module_root / "python"
    if not python_dir.is_dir():
        python_dir = module_root / "python"

    python_str = str(python_dir)
    if python_str not in sys.path:
        sys.path.insert(0, python_str)
        logger.debug("Added %s to sys.path for dcc_mcp_maya package discovery", python_str)


_ensure_package_importable()


def _get_version() -> str:
    try:
        from dcc_mcp_maya.__version__ import __version__  # noqa: PLC0415

        return __version__
    except Exception:
        return "0.0.0"


VERSION = _get_version()

# ── module-level state ────────────────────────────────────────────────────────
_handle = None
_menu_name = "DccMcpMenu"
_restart_lock = threading.Lock()  # prevent overlapping restart calls


# ── standalone detection ──────────────────────────────────────────────────────


def _is_interactive() -> bool:
    """Return True when Maya is running in interactive (GUI) mode."""
    try:
        return not cmds.about(batch=True)
    except Exception:
        return False


# ── plugin API version declaration ──────────────────────────────────────────


def maya_useNewAPI() -> None:
    """Declare Python API 2.0 to Maya."""


# ── plugin init ───────────────────────────────────────────────────────────────


def initializePlugin(plugin):
    """Called by Maya when the plugin is loaded."""
    om.MFnPlugin(plugin, VENDOR, VERSION)
    try:
        if _is_interactive():
            _add_menu()
        _start()
    except Exception as exc:
        logger.error("dcc-mcp-maya plugin failed to initialize: %s", exc)
        raise RuntimeError(f"dcc-mcp-maya init failed: {exc}") from exc


def uninitializePlugin(plugin):
    """Called by Maya when the plugin is unloaded."""
    om.MFnPlugin(plugin)
    try:
        _stop_blocking()
        if _is_interactive():
            _remove_menu()
        logger.info("dcc-mcp-maya plugin unloaded")
    except Exception as exc:
        logger.warning("dcc-mcp-maya cleanup error: %s", exc)


# ── server helpers ────────────────────────────────────────────────────────────


def _resolve_config():
    """Read all config from env vars and return as a dict."""
    port = int(os.environ.get("DCC_MCP_MAYA_PORT", "0"))
    server_name = os.environ.get("DCC_MCP_MAYA_SERVER_NAME", "maya-mcp")
    gateway_port_str = os.environ.get("DCC_MCP_GATEWAY_PORT", str(_DEFAULT_GATEWAY_PORT))
    try:
        gateway_port = int(gateway_port_str)
    except ValueError:
        gateway_port = _DEFAULT_GATEWAY_PORT
    registry_dir = os.environ.get("DCC_MCP_REGISTRY_DIR") or None
    try:
        dcc_version = str(cmds.about(version=True))
    except Exception:
        dcc_version = None
    return {
        "port": port,
        "server_name": server_name,
        "gateway_port": gateway_port if gateway_port > 0 else None,
        "registry_dir": registry_dir,
        "dcc_version": dcc_version,
    }


def _start() -> None:
    """Start the MCP server (called from Maya main thread)."""
    global _handle
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        cfg = _resolve_config()
        _handle = dcc_mcp_maya.start_server(**cfg)
        _print_startup_info(cfg)
    except Exception as exc:
        logger.error("Failed to start MCP server: %s", exc)
        raise


def _print_startup_info(cfg: dict) -> None:
    """Print startup info to Maya console and script editor."""
    import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

    instance_url = _handle.mcp_url() if _handle else "<not running>"
    gateway_port = cfg.get("gateway_port") or 0
    dcc_version = cfg.get("dcc_version") or "unknown"

    srv = _srv_mod._server_instance  # noqa: SLF001
    is_gw = bool(srv and getattr(srv, "is_gateway", False))

    # ── banner ────────────────────────────────────────────────────────────────
    border = "=" * 60
    lines = [
        border,
        f"  dcc-mcp-maya v{VERSION}  |  Maya {dcc_version}",
        border,
        f"  Instance URL : {instance_url}",
    ]

    if gateway_port > 0:
        gw_url = f"http://127.0.0.1:{gateway_port}"
        if is_gw:
            lines.append(f"  Gateway URL  : {gw_url}  [THIS INSTANCE IS GATEWAY]")
            lines.append(f"  Connect MCP client to: {gw_url}/mcp")
        else:
            lines.append(f"  Gateway URL  : {gw_url}  [registered as instance]")
            lines.append(f"  Connect MCP client to: {gw_url}/mcp  (via gateway)")
        lines.append("  Gateway tools: list_dcc_instances / connect_to_dcc")
    else:
        lines.append(f"  Connect MCP client to: {instance_url}")
        lines.append("  (Gateway disabled — set DCC_MCP_GATEWAY_PORT=9765 to enable)")

    lines.append(border)

    banner = "\n".join(lines)

    # Print to Maya script editor / output window
    print(banner)  # noqa: T201 — intentional console output

    # Also show in Maya viewport HUD (interactive mode only)
    if _is_interactive() and _handle:
        try:
            if is_gw:
                hud_msg = f"DCC MCP <b>[GATEWAY]</b> {gw_url}/mcp"
            elif gateway_port > 0:
                hud_msg = f"DCC MCP <b>[instance]</b> → gateway {gw_url}/mcp"
            else:
                hud_msg = f"DCC MCP ready: {instance_url}"
            cmds.inViewMessage(amg=hud_msg, pos="topCenter", fade=True, fadeStayTime=4000)
        except Exception:
            pass  # viewport HUD is cosmetic, never block startup


def _stop_blocking() -> None:
    """Stop the server, blocking until fully shut down.

    Safe to call from any thread.  Uses the standard stop_server() path
    which calls handle.shutdown() (blocking).  Only used during plugin
    unload (``uninitializePlugin``), where blocking is acceptable.
    """
    global _handle
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        dcc_mcp_maya.stop_server()
        _handle = None
    except Exception as exc:
        logger.warning("Failed to stop MCP server: %s", exc)


def _stop_async() -> None:
    """Signal shutdown without blocking the Maya main thread.

    Sends a non-blocking shutdown signal, then waits in a background
    thread.  Used by the Restart menu item to avoid freezing Maya.
    """
    global _handle
    try:
        import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

        # Signal shutdown (non-blocking — returns immediately)
        srv = _srv_mod._server_instance  # noqa: SLF001
        if srv and srv._handle:
            srv._handle.signal_shutdown()

        # Deregister singleton so start_server() creates a fresh instance
        _srv_mod._server_instance = None  # noqa: SLF001
        _handle = None
    except Exception as exc:
        logger.warning("Failed to signal MCP server shutdown: %s", exc)


def _server_url() -> str:
    if _handle is not None:
        try:
            return _handle.mcp_url()
        except Exception:
            pass
    return "<not running>"


# ── menu ─────────────────────────────────────────────────────────────────────


def _add_menu() -> None:
    try:
        if cmds.menu(_menu_name, exists=True):
            cmds.deleteUI(_menu_name)
        cmds.menu(_menu_name, label="DCC MCP", parent="MayaWindow", tearOff=False)
        cmds.menuItem(label="Show MCP URL", command=lambda *_: _show_url())
        cmds.menuItem(label="Restart MCP Server", command=lambda *_: _restart_deferred())
        cmds.menuItem(label="Stop MCP Server", command=lambda *_: _stop_blocking())
        cmds.menuItem(divider=True)
        cmds.menuItem(label="Open MCP in Browser", command=lambda *_: _open_browser())
    except Exception as exc:
        logger.warning("Could not add DCC MCP menu: %s", exc)


def _remove_menu() -> None:
    try:
        if cmds.menu(_menu_name, exists=True):
            cmds.deleteUI(_menu_name)
    except Exception:
        pass


def _show_url() -> None:
    import dcc_mcp_maya.server as _srv_mod  # noqa: PLC0415

    srv = _srv_mod._server_instance  # noqa: SLF001
    instance_url = _server_url()
    gateway_port = int(os.environ.get("DCC_MCP_GATEWAY_PORT", str(_DEFAULT_GATEWAY_PORT)))
    is_gw = bool(srv and getattr(srv, "is_gateway", False))

    if gateway_port > 0:
        gw_url = f"http://127.0.0.1:{gateway_port}/mcp"
        if is_gw:
            msg = f"Gateway (this instance):\n  {gw_url}\n\nInstance URL:\n  {instance_url}"
        else:
            msg = f"Gateway:\n  {gw_url}\n\nThis instance:\n  {instance_url}"
    else:
        msg = f"MCP Server URL:\n  {instance_url}"

    cmds.confirmDialog(title="DCC MCP — Server URLs", message=msg, button=["OK"])


def _restart_deferred() -> None:
    """Restart the MCP server without blocking the Maya main thread.

    Pattern:
      1. Signal shutdown (non-blocking, returns immediately).
      2. Spawn a background thread that waits ~0.5 s for the Rust runtime
         to drain, then reschedules _start() back on the Maya main thread
         via ``maya.utils.executeDeferred``.
    """
    if not _restart_lock.acquire(blocking=False):
        cmds.warning("DCC MCP: restart already in progress, please wait.")
        return

    cmds.inViewMessage(amg="DCC MCP: restarting…", pos="topCenter", fade=True)
    _stop_async()

    def _bg_restart():
        import time

        time.sleep(0.6)  # let the Rust runtime finish shutting down

        try:
            import maya.utils  # noqa: PLC0415

            maya.utils.executeDeferred(_main_thread_start)
        except Exception as exc:
            logger.error("DCC MCP: background restart failed: %s", exc)
        finally:
            _restart_lock.release()

    def _main_thread_start():
        try:
            _start()
        except Exception as exc:
            logger.error("DCC MCP: restart _start() failed: %s", exc)

    threading.Thread(target=_bg_restart, daemon=True, name="dcc-mcp-restart").start()


def _open_browser() -> None:
    url = _server_url()
    if url and url != "<not running>":
        import webbrowser  # noqa: PLC0415

        webbrowser.open(url)
    else:
        cmds.warning("MCP server is not running.")
