"""dcc_mcp_maya — Maya plugin entry point.

Loads the MCP Streamable HTTP server inside Maya.

Installation
------------
Copy this file (or create a symlink) into a directory on ``MAYA_PLUG_IN_PATH``.
Load it via **Window > Settings/Preferences > Plug-in Manager**.

Alternatively, add to ``userSetup.py``::

    import maya.cmds as cmds
    cmds.loadPlugin("dcc_mcp_maya")

Configuration
-------------
Environment variables (optional, read at plugin load time):

``DCC_MCP_MAYA_PORT``
    TCP port for the MCP HTTP server.  Default: ``8765``.

``DCC_MCP_MAYA_SERVER_NAME``
    Name advertised in the MCP ``initialize`` response.  Default: ``"maya-mcp"``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os

# Import third-party modules
import maya.OpenMaya as om
import maya.cmds as cmds
import maya.utils

logger = logging.getLogger(__name__)

VENDOR = "dcc-mcp"
VERSION = "0.3.0"

# ── module-level server handle ────────────────────────────────────────────────
_handle = None
_menu_name = "DccMcpMenu"


# ── plugin init ───────────────────────────────────────────────────────────────

def initializePlugin(plugin):
    """Called by Maya when the plugin is loaded."""
    fn = om.MFnPlugin(plugin, VENDOR, VERSION)
    try:
        _add_menu()
        _start()
        logger.info("dcc-mcp-maya plugin v%s loaded — %s", VERSION, _server_url())
    except Exception as exc:
        logger.error("dcc-mcp-maya plugin failed to initialize: %s", exc)
        raise RuntimeError(f"dcc-mcp-maya init failed: {exc}") from exc


def uninitializePlugin(plugin):
    """Called by Maya when the plugin is unloaded."""
    om.MFnPlugin(plugin)
    try:
        _stop()
        _remove_menu()
        logger.info("dcc-mcp-maya plugin unloaded")
    except Exception as exc:
        logger.warning("dcc-mcp-maya cleanup error: %s", exc)


# ── server helpers ────────────────────────────────────────────────────────────

def _start() -> None:
    global _handle
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        port = int(os.environ.get("DCC_MCP_MAYA_PORT", "8765"))
        server_name = os.environ.get("DCC_MCP_MAYA_SERVER_NAME", "maya-mcp")
        _handle = dcc_mcp_maya.start_server(port=port, server_name=server_name)
        logger.info("MCP server started at %s", _handle.mcp_url())
    except Exception as exc:
        logger.error("Failed to start MCP server: %s", exc)
        raise


def _stop() -> None:
    global _handle
    try:
        import dcc_mcp_maya  # noqa: PLC0415

        dcc_mcp_maya.stop_server()
        _handle = None
    except Exception as exc:
        logger.warning("Failed to stop MCP server: %s", exc)


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
        cmds.menuItem(label="Restart MCP Server", command=lambda *_: _restart())
        cmds.menuItem(label="Stop MCP Server", command=lambda *_: _stop())
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
    url = _server_url()
    cmds.confirmDialog(title="MCP Server URL", message=f"Connect your MCP host to:\n\n{url}", button=["OK"])


def _restart() -> None:
    _stop()
    _start()
    cmds.inViewMessage(amg=f"MCP server restarted at <b>{_server_url()}</b>", pos="topCenter", fade=True)


def _open_browser() -> None:
    url = _server_url()
    if url and url != "<not running>":
        import webbrowser  # noqa: PLC0415
        webbrowser.open(url)
    else:
        cmds.warning("MCP server is not running.")
