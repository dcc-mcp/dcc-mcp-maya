"""Maya RPYC client implementation.

This module provides a client for communicating with Maya through RPYC.
It implements the MayaRPyCClient class for connecting to Maya RPYC servers
and executing Maya commands and scripts.
"""

# Import built-in modules
import logging
from typing import Any, Dict, Optional

# Import third-party modules

# Import dcc-mcp-rpyc modules
from dcc_mcp_rpyc.client import BaseDCCClient, get_client as rpyc_get_client

# Configure logging
logger = logging.getLogger(__name__)


# Export symbols
__all__ = ["MayaRPyCClient", "get_client", "get_maya_client"]


class MayaRPyCClient(BaseDCCClient):
    """Client for connecting to Maya RPYC servers.

    This class provides Maya-specific functionality for connecting to Maya RPYC servers
    and executing Maya commands and scripts.

    Attributes:
        host: Host of the Maya RPYC server
        port: Port of the Maya RPYC server
        connection: Active RPYC connection
        _cmds: Maya commands proxy

    """

    def __init__(
        self,
        dcc_name: str = "maya",
        host: Optional[str] = "localhost",
        port: Optional[int] = None,
        auto_connect: bool = True,
        connection_timeout: float = 5.0,
        registry_path: Optional[str] = None,
    ):
        """Initialize the Maya RPYC client.

        Args:
            dcc_name: Name of the DCC (default: 'maya')
            host: Host of the Maya RPYC server (default: 'localhost')
            port: Port of the Maya RPYC server (default: None, auto-discover)
            auto_connect: Whether to automatically connect (default: True)
            connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
            registry_path: Optional path to the registry file (default: None)

        """
        super().__init__(dcc_name, host, port, auto_connect, connection_timeout, registry_path)
        self._cmds = None

    @property
    def cmds(self):
        """Get the Maya commands proxy object.

        This property provides direct access to Maya commands through RPyC.
        It allows using Maya commands as if they were local functions.

        Returns:
            The Maya commands proxy object or None if not available

        """
        if not self.ensure_connected():
            return None

        if self._cmds is None:
            try:
                self._cmds = self.connection.modules.maya.cmds
                logger.debug("Retrieved Maya commands proxy")
            except Exception as e:
                logger.error(f"Error retrieving Maya commands proxy: {e}")
                return None

        return self._cmds

    def execute_mel(self, script: str) -> Any:
        """Execute a MEL script in Maya.

        Args:
            script: MEL script to execute

        Returns:
            The result of the MEL script execution

        Raises:
            ConnectionError: If not connected to Maya

        """
        if not self.ensure_connected():
            raise ConnectionError("Not connected to Maya")

        try:
            return self.connection.modules.maya.mel.eval(script)
        except Exception as e:
            logger.error(f"Error executing MEL script: {e}")
            raise

    def execute_cmd(self, command: str, *args, **kwargs) -> Any:
        """Execute a Maya command.

        Args:
            command: Maya command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
            The result of the command execution

        Raises:
            ConnectionError: If not connected to Maya

        """
        # Check if we're connected and have Maya commands available
        if not self.ensure_connected() or self._cmds is None:
            raise ConnectionError("Maya commands not available")

        try:
            cmd_func = getattr(self._cmds, command)
            return cmd_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing Maya command '{command}': {e}")
            raise

    def create_primitive(self, primitive_type: str, **kwargs) -> Any:
        """Create a primitive object in Maya.

        Args:
            primitive_type: Type of primitive to create (cube, sphere, cylinder, cone, plane, torus)
            **kwargs: Additional arguments for the primitive creation command

        Returns:
            The result of the primitive creation command

        Raises:
            ConnectionError: If not connected to Maya
            ValueError: If the primitive type is not supported

        """
        # Check if we're connected and have Maya commands available
        if not self.ensure_connected() or self._cmds is None:
            raise ConnectionError("Maya commands not available")

        # Map of primitive types to Maya commands
        primitive_commands = {
            "cube": self._cmds.polyCube,
            "sphere": self._cmds.polySphere,
            "cylinder": self._cmds.polyCylinder,
            "cone": self._cmds.polyCone,
            "plane": self._cmds.polyPlane,
            "torus": self._cmds.polyTorus,
        }

        # Check if the primitive type is supported
        if primitive_type not in primitive_commands:
            raise ValueError(f"Unsupported primitive type: {primitive_type}")

        try:
            # Create the primitive
            return primitive_commands[primitive_type](**kwargs)
        except Exception as e:
            logger.error(f"Error creating primitive '{primitive_type}': {e}")
            raise

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current Maya scene.

        Returns:
            Dict with scene information

        Raises:
            ConnectionError: If not connected to Maya

        """
        # Check if we're connected and have Maya commands available
        if not self.ensure_connected() or self._cmds is None:
            raise ConnectionError("Maya commands not available")

        try:
            # Get scene path
            scene_path = self.execute_cmd("file", query=True, sceneName=True) or ""

            # Get selection
            selection = self.execute_cmd("ls", selection=True) or []

            # Get all objects in the scene
            all_objects = self.execute_cmd("ls", long=True) or []

            # Get scene stats
            stats = {
                "num_objects": len(all_objects),
                "num_selected": len(selection),
            }

            return {
                "scene_path": scene_path,
                "selection": selection,
                "stats": stats,
            }
        except Exception as e:
            logger.error(f"Error getting scene information: {e}")
            raise

    def action_call(self, action_name: str, function_name: str = None, context: Dict[str, Any] = None) -> Any:
        """Call an action function in Maya.

        This method uses the dcc_mcp_core action manager to call the specified action function.

        Args:
            action_name: Name of the action
            function_name: Name of the function to call (default: None, will use 'main' if None)
            context: Context dictionary with additional parameters

        Returns:
            The result of the action function call, typically an ActionResultModel

        """
        if not context:
            context = {}

        # Ensure we're connected to Maya
        if not self.is_connected():
            self.reconnect()

        try:
            # Use dcc_mcp_core actions manager
            from dcc_mcp_core.actions.manager import call_action_function

            # Add Maya modules to context for action to use
            maya_context = context.copy()
            maya_context["_maya_rpyc_client"] = self
            maya_context["_maya_cmds"] = self._cmds

            # Default to 'main' function if none specified
            if function_name is None:
                function_name = "main"

            return call_action_function("maya", action_name, function_name, maya_context)
        except Exception as e:
            logger.error(f"Error calling action function '{action_name}.{function_name}': {e}")
            raise

    def plugin_call(self, plugin_name: str, context: Dict[str, Any] = None) -> Any:
        """Call a plugin function in Maya (Legacy method).

        This method is maintained for backward compatibility.
        It now redirects to action_call with the plugin_name as action_name and 'func_call' as function_name.

        Args:
            plugin_name: Name of the plugin (now treated as action_name)
            context: Context dictionary with additional parameters

        Returns:
            The result of the plugin/action function call

        """
        logger.warning("plugin_call is deprecated, use action_call instead")
        return self.action_call(plugin_name, "func_call", context)


def get_maya_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    auto_connect: bool = True,
    connection_timeout: float = 5.0,
    registry_path: Optional[str] = None,
) -> MayaRPyCClient:
    """Get a Maya RPYC client instance.

    This function returns a Maya RPYC client instance, either from the global
    connection pool or by creating a new one if necessary.

    Args:
        host: Host of the Maya RPYC server (default: None, auto-discover)
        port: Port of the Maya RPYC server (default: None, auto-discover)
        auto_connect: Whether to automatically connect (default: True)
        connection_timeout: Timeout for connection attempts in seconds (default: 5.0)
        registry_path: Optional path to the registry file (default: None)

    Returns:
        A Maya RPYC client instance

    """
    # Get a client from the global connection pool
    client = rpyc_get_client("maya", host, port, auto_connect, connection_timeout, registry_path)

    # If the client is not a MayaRPyCClient, create a new one
    if not isinstance(client, MayaRPyCClient):
        client = MayaRPyCClient(
            dcc_name="maya",
            host=host,
            port=port,
            auto_connect=auto_connect,
            connection_timeout=connection_timeout,
            registry_path=registry_path,
        )

    return client


def get_client(
    dcc_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    auto_connect: bool = True,
    connection_timeout: float = 5.0,
    registry_path: Optional[str] = None,
) -> MayaRPyCClient:
    return get_maya_client(
        host=host,
        port=port,
        auto_connect=auto_connect,
        connection_timeout=connection_timeout,
        registry_path=registry_path,
    )
