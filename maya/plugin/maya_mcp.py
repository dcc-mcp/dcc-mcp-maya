"""Maya MCP Plugin.

This plugin provides RPYC server functionality for Maya, allowing remote control of Maya
through the Model Context Protocol (MCP).

To use this plugin:
1. Load it through Maya's Plugin Manager
2. The plugin will add a menu item to start the MCP server
3. Alternatively, call the initialize() function from a script

Author: DCC-MCP Team
Version: 1.0.0
"""

# Import built-in modules
import logging

# Import Maya modules
from maya import cmds
import maya.api.OpenMaya as om
import maya.mel as mel

# Configure logging
logger = logging.getLogger("dcc_mcp_maya")
from dcc_mcp_maya.__version__ import __version__

# Global variables
MAYA_SERVER = None
PLUGIN_NAME = "MayaMCPPlugin"
PLUGIN_VERSION = __version__
VENDOR = "LongHao"


# Try to import DCC-MCP-RPYC modules
try:
    # First try to import from installed packages
    from dcc_mcp_rpyc.server import DCCRPyCService, create_dcc_server

    logger.info("Successfully imported dcc_mcp_rpyc modules from installed packages")
except ImportError as e:
    logger.warning(f"Could not import dcc_mcp_rpyc from installed packages: {e}")


def maya_useNewAPI():
    """Tell Maya this plugin uses the Python API 2.0."""
    pass


class MayaService(DCCRPyCService):
    """RPYC service that exposes Maya's functionality.

    This class implements the DCCRPyCService interface and provides methods for
    executing Maya commands, MEL scripts, and creating primitives.
    """

    def on_connect(self, conn):
        """Called when a client connects.

        Args:
            conn: The RPYC connection object

        """
        super().on_connect(conn)
        logger.info("Maya client connected")

    def on_disconnect(self, conn):
        """Called when a client disconnects.

        Args:
            conn: The RPYC connection object

        """
        super().on_disconnect(conn)
        logger.info("Maya client disconnected")

    def get_scene_info(self):
        """Get information about the current Maya scene.

        Returns:
            Dict with scene information

        """
        try:
            current_file = cmds.file(q=True, sceneName=True) or "untitled"
            selection = cmds.ls(selection=True) or []
            objects = cmds.ls(type="transform") or []
            cameras = cmds.ls(type="camera") or []
            lights = cmds.ls(type="light") or []
            meshes = cmds.ls(type="mesh") or []
            materials = cmds.ls(type="material") or []

            return {
                "file": current_file,
                "selection": selection,
                "objects": {
                    "count": len(objects),
                    "items": objects[:10],  # Limit to first 10 for brevity
                },
                "cameras": {"count": len(cameras), "items": cameras},
                "lights": {"count": len(lights), "items": lights},
                "meshes": {
                    "count": len(meshes),
                    "items": meshes[:10],  # Limit to first 10 for brevity
                },
                "materials": {
                    "count": len(materials),
                    "items": materials[:10],  # Limit to first 10 for brevity
                },
            }
        except Exception as e:
            logger.error(f"Error getting scene info: {e}")
            return {"error": str(e)}

    @DCCRPyCService.with_scene_info
    def exposed_execute_cmd(self, cmd_name, *args, **kwargs):
        """Execute a Maya command.

        Args:
            cmd_name: Name of the Maya command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
            The result of the command execution

        """
        try:
            # Get the command from Maya's commands module
            cmd = getattr(cmds, cmd_name)

            # Execute the command
            result = cmd(*args, **kwargs)

            return result
        except AttributeError:
            error_msg = f"Command '{cmd_name}' not found in Maya"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error executing command '{cmd_name}': {e}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DCCRPyCService.with_scene_info
    def exposed_execute_mel(self, script):
        """Execute a MEL script in Maya.

        Args:
            script: MEL script to execute

        Returns:
            The result of the script execution

        """
        try:
            result = cmds.mel.eval(script)
            return result
        except Exception as e:
            error_msg = f"Error executing MEL script: {e}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DCCRPyCService.with_scene_info
    def exposed_create_primitive(self, primitive_type, **kwargs):
        """Create a primitive object in Maya.

        Args:
            primitive_type: Type of primitive to create (cube, sphere, cylinder, cone, plane, torus)
            **kwargs: Additional arguments for the primitive creation command

        Returns:
            The result of the primitive creation command

        """
        try:
            primitive_map = {
                "cube": cmds.polyCube,
                "sphere": cmds.polySphere,
                "cylinder": cmds.polyCylinder,
                "cone": cmds.polyCone,
                "plane": cmds.polyPlane,
                "torus": cmds.polyTorus,
            }

            if primitive_type not in primitive_map:
                error_msg = f"Unknown primitive type: {primitive_type}. Valid types: {list(primitive_map.keys())}"
                logger.error(error_msg)
                return {"error": error_msg}

            # Create the primitive
            result = primitive_map[primitive_type](**kwargs)

            return result
        except Exception as e:
            error_msg = f"Error creating primitive: {e}"
            logger.error(error_msg)
            return {"error": error_msg}

    @DCCRPyCService.with_scene_info
    def exposed_plugin_call(self, plugin_name, context):
        """Call a plugin function in Maya.

        Args:
            plugin_name: Name of the plugin
            context: Context dictionary with additional parameters

        Returns:
            The result of the plugin function call

        """
        try:
            # This is a placeholder for actual plugin functionality
            # In a real implementation, this would dispatch to the appropriate plugin
            return {"plugin": plugin_name, "context": context, "status": "success"}
        except Exception as e:
            error_msg = f"Error calling plugin: {e}"
            logger.error(error_msg)
            return {"error": error_msg}


def initialize(port=None):
    """Initialize the Maya MCP server.

    This function starts the RPYC server in a separate thread to avoid blocking Maya.

    Args:
        port (int, optional): Port number to use for the RPYC server. If None, a random port will be used.

    Returns:
        int: The port number the server is running on, or None if the server failed to start.

    """
    global MAYA_SERVER

    try:
        # Check if the server is already running
        if MAYA_SERVER is not None and MAYA_SERVER.is_running():
            logger.info(f"RPYC server is already running on port {MAYA_SERVER.port}")
            return MAYA_SERVER.port

        # Create the server
        MAYA_SERVER = create_dcc_server(dcc_name="maya", service_class=MayaService, port=port or 0)

        # Start the server in a thread-safe manner
        try:
            import maya.utils as utils

            result = utils.executeInMainThreadWithResult(lambda: MAYA_SERVER.start(threaded=True))
        except ImportError:
            # If we're not in Maya, just start the server directly
            result = MAYA_SERVER.start(threaded=True)

        if result:
            logger.info(f"Started Maya RPYC server on port {MAYA_SERVER.port}")
            return MAYA_SERVER.port
        else:
            logger.error("Failed to start Maya RPYC server")
            MAYA_SERVER = None
            return None
    except Exception as e:
        logger.error(f"Failed to initialize Maya MCP server: {e}")
        # Clean up if initialization failed
        if MAYA_SERVER is not None:
            try:
                MAYA_SERVER.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up after initialization error: {cleanup_error}")
            MAYA_SERVER = None
        return None


def stop_server():
    """Stop the Maya MCP server."""
    global MAYA_SERVER

    try:
        if MAYA_SERVER is not None and MAYA_SERVER.is_running():
            logger.info("Stopping RPYC server")
            MAYA_SERVER.cleanup()
            MAYA_SERVER = None
        else:
            logger.info("RPYC server is not running")
    except Exception as e:
        logger.error(f"Failed to stop Maya MCP server: {e}")


def initializePlugin(mobject):
    """Initialize the plugin when it's loaded in Maya.

    This function is called by Maya when the plugin is loaded.

    Args:
        mobject (MObject): Maya plugin object

    """
    plugin_fn = om.MFnPlugin(mobject, VENDOR, PLUGIN_VERSION, "Any")

    try:
        # Add a menu item to start the server
        if cmds.about(batch=True):
            # In batch mode, start the server automatically
            initialize()
        else:
            # In UI mode, add a menu item
            if not cmds.menu("MCPMenu", exists=True):
                # Create the menu if it doesn't exist
                main_window = mel.eval("$tmp = $gMainWindow")
                mcp_menu = cmds.menu("MCPMenu", label="MCP", parent=main_window, tearOff=True)

                # Add menu items
                cmds.menuItem(label="Start MCP Server", command=lambda x: initialize())

                cmds.menuItem(label="Stop MCP Server", command=lambda x: stop_server())

                cmds.menuItem(divider=True)

                cmds.menuItem(
                    label="About MCP Plugin",
                    command=lambda x: cmds.confirmDialog(
                        title="About MCP Plugin",
                        message=f"Maya MCP Plugin v{PLUGIN_VERSION}\n\nThis plugin allows remote control of Maya through the Model Context Protocol (MCP).",
                        button=["OK"],
                        defaultButton="OK",
                    ),
                )

        logger.info(f"Maya MCP Plugin v{PLUGIN_VERSION} initialized")
    except Exception as e:
        logger.error(f"Failed to initialize plugin: {e}")
        raise


def uninitializePlugin(mobject):
    """Clean up when the plugin is unloaded.

    This function is called by Maya when the plugin is unloaded.

    Args:
        mobject (MObject): Maya plugin object

    """
    logger.info("Maya MCP Plugin uninitialized")
    try:
        # Clean up the server if it's running
        stop_server()

        # Remove the menu if it exists
        if cmds.menu("MCPMenu", exists=True):
            cmds.deleteUI("MCPMenu", menu=True)

        logger.info("Maya MCP Plugin uninitialized")
    except Exception as e:
        logger.error(f"Failed to uninitialize plugin: {e}")
        raise
