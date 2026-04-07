"""DCC-MCP Maya Plugin.

This file is the Maya plugin entry point. Load it through Maya's Plugin Manager
(Window > Settings/Preferences > Plug-in Manager) or via:

    import maya.cmds as cmds
    cmds.loadPlugin("/path/to/dcc_mcp_maya.py")

The plugin:
1. Starts a DCCServer (dcc-mcp-ipc) bound to MayaRPyCService.
2. Registers the service so external clients can auto-discover it.
3. Adds a "DCC MCP" menu to Maya with Start/Stop controls.

Dependencies (must be on PYTHONPATH or installed into Maya's Python):
    - dcc-mcp-core  >= 0.12.0
    - dcc-mcp-ipc   >= 2.0.0   (package name: dcc-mcp-ipc, module: dcc_mcp_ipc)
    - rpyc          >= 6.0.0
"""

# Import built-in modules
import logging

# Import Maya modules
import maya.api.OpenMaya as om
from maya import cmds
from maya import mel

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("dcc_mcp_maya.plugin")

# ── Plugin metadata ──
PLUGIN_NAME = "dcc_mcp_maya"
VENDOR = "loonghao"

_server = None  # DCCServer instance


def maya_useNewAPI():
    """Declare that this plugin uses Maya Python API 2.0."""
    pass


# ── Server lifecycle ──

def start_server(port: int = 0, use_zeroconf: bool = True) -> int:
    """Start the MayaRPyCService inside Maya.

    Args:
        port: Port to listen on. 0 means auto-select.
        use_zeroconf: Register with ZeroConf for auto-discovery.

    Returns:
        The actual port the server is listening on.

    """
    global _server
    if _server is not None and _server.is_running():
        logger.warning("DCC-MCP server is already running on port %s", _server.port)
        return _server.port

    from dcc_mcp_maya.service import MayaRPyCService
    from dcc_mcp_ipc.server.dcc import DCCServer

    _server = DCCServer(
        dcc_name="maya",
        service_class=MayaRPyCService,
        port=port,
        use_zeroconf=use_zeroconf,
    )
    actual_port = _server.start(threaded=True)
    if not actual_port:
        raise RuntimeError("DCC-MCP: Failed to start MayaRPyCService")

    logger.info("DCC-MCP Maya server started on port %s", actual_port)
    cmds.inViewMessage(
        assistMessage=f"DCC-MCP server started on port <hl>{actual_port}</hl>",
        position="topCenter",
        fade=True,
    )
    return actual_port


def stop_server() -> None:
    """Stop the running MayaRPyCService."""
    global _server
    if _server is None or not _server.is_running():
        logger.warning("DCC-MCP server is not running")
        return

    _server.stop()
    _server = None
    logger.info("DCC-MCP Maya server stopped")
    cmds.inViewMessage(
        assistMessage="DCC-MCP server stopped",
        position="topCenter",
        fade=True,
    )


def get_server_port() -> int:
    """Return the current server port, or -1 if not running."""
    if _server and _server.is_running():
        return _server.port
    return -1


# ── Maya Plugin callbacks ──

def _add_menu():
    """Add the DCC MCP menu to Maya's main window."""
    menu_name = "DccMcpMenu"
    if cmds.menu(menu_name, exists=True):
        cmds.deleteUI(menu_name)

    main_window = mel.eval("$tmp = $gMainWindow")
    cmds.menu(menu_name, label="DCC MCP", parent=main_window, tearOff=False)
    cmds.menuItem(label="Start Server", command=lambda _: start_server())
    cmds.menuItem(label="Stop Server", command=lambda _: stop_server())
    cmds.menuItem(divider=True)
    cmds.menuItem(
        label="Server Status",
        command=lambda _: cmds.confirmDialog(
            title="DCC-MCP Status",
            message=f"Port: {get_server_port()}" if get_server_port() > 0 else "Server not running",
            button=["OK"],
        ),
    )


def _remove_menu():
    """Remove the DCC MCP menu from Maya."""
    if cmds.menu("DccMcpMenu", exists=True):
        cmds.deleteUI("DccMcpMenu")


def initializePlugin(plugin):
    """Called by Maya when the plugin is loaded."""
    fn = om.MFnPlugin(plugin, VENDOR, "1.0")
    try:
        _add_menu()
        start_server()
        logger.info("DCC-MCP Maya plugin initialized (v%s)", fn.version)
    except Exception as e:
        logger.error("Failed to initialize DCC-MCP plugin: %s", e)
        raise


def uninitializePlugin(plugin):
    """Called by Maya when the plugin is unloaded."""
    om.MFnPlugin(plugin)
    try:
        stop_server()
        _remove_menu()
        logger.info("DCC-MCP Maya plugin unloaded")
    except Exception as e:
        logger.error("Error during DCC-MCP plugin unload: %s", e)
        raise
