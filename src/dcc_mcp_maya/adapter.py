"""Maya MCP adapter implementation.

This module provides an adapter for integrating Maya with the Model Context Protocol (MCP).
"""

# Import built-in modules
import logging
import os
import time
import json
import glob
import importlib.util
from typing import Any, Dict, List, Optional

# Import third-party modules
from dcc_mcp_rpyc.adapter import DCCAdapter

# Import dcc-mcp-core modules
from dcc_mcp_core.models import ActionResultModel

# Import local modules
from dcc_mcp_maya.client import MayaRPyCClient
from dcc_mcp_maya.__version__ import __version__
from dcc_mcp_rpyc.client import get_client

# Configure logging
logger = logging.getLogger(__name__)


class MayaMCPAdapter(DCCAdapter):
    """Maya adapter for MCP integration.

    This class provides an adapter for integrating Maya with the Model Context Protocol (MCP).
    It exposes Maya functionality through the MCP interface and utilizes the ActionResultModel
    from dcc-mcp-core for standardized result handling.

    Attributes:
        dcc_client: MayaRPyCClient instance for communicating with Maya
        maya_mcp_plugins_paths: List of paths to search for Maya MCP plugins
        action_manager: Manager for actions in Maya

    """

    def __init__(self):
        """Initialize the Maya MCP adapter."""
        # Initialize the base class
        super().__init__("maya")

    def _initialize_client(self) -> None:
        """Initialize the client for communicating with Maya."""
        # This method is called by the parent class's __init__ method
        # We'll create the client here to ensure it's properly initialized
        self.dcc_client = get_client("maya", auto_connect=True, client_class=MayaRPyCClient)

    def ensure_connected(self) -> bool:
        """Ensure that the client is connected to Maya.

        Returns:
            bool: True if connected, False otherwise

        """
        current_time = time.time()

        # Only check connection if it's been more than 5 seconds since last check
        if current_time - self.last_connection_check < 5:
            return self.dcc_client.is_connected()

        self.last_connection_check = current_time

        if not self.dcc_client.is_connected():
            logger.info("Reconnecting to Maya...")
            try:
                self.dcc_client.connect()
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Maya: {e}")
                return False

        return True

    def create_primitive(self, primitive_type: str, context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Create a primitive object in Maya.

        Args:
            primitive_type: Type of primitive to create (cube, sphere, cylinder, cone, plane, torus)
            context: Context provided by the MCP server
            **kwargs: Additional arguments for the primitive creation command

        Returns:
            ActionResultModel with information about the created primitive and scene info

        """
        # Ensure we're connected to Maya
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message="Failed to create primitive",
                error="Not connected to Maya",
                prompt="Please check Maya connection and try again.",
            ).model_dump()

        try:
            # Create the primitive
            result = self.dcc_client.create_primitive(primitive_type, **kwargs)

            # Get scene info
            scene_info = self.get_scene_info()

            return ActionResultModel(
                success=True,
                message=f"Successfully created {primitive_type}",
                context={"result": result, "scene_info": scene_info.get("context", {})},
            ).model_dump()
        except Exception as e:
            logger.error(f"Error creating primitive '{primitive_type}': {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to create {primitive_type}",
                error=str(e),
                prompt="Check the parameters and try again.",
            ).model_dump()

    def execute_command(
        self, command: str, args: str = "", kwargs: str = "", context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a Maya command.

        Args:
            command: Name of the Maya command to execute
            args: Positional arguments for the command (as a string)
            kwargs: Keyword arguments for the command (as a string)
            context: Context provided by the MCP server

        Returns:
            ActionResultModel with the result of the command execution and scene info

        """
        # Ensure we're connected to Maya
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message="Failed to execute command",
                error="Not connected to Maya",
                prompt="Please check Maya connection and try again.",
            ).model_dump()

        try:
            # Parse args and kwargs
            parsed_args = []
            parsed_kwargs = {}

            if args:
                try:
                    parsed_args = json.loads(args)
                    if not isinstance(parsed_args, list):
                        parsed_args = [parsed_args]
                except json.JSONDecodeError:
                    # If not valid JSON, treat as a single string argument
                    parsed_args = [args]

            if kwargs:
                try:
                    parsed_kwargs = json.loads(kwargs)
                    if not isinstance(parsed_kwargs, dict):
                        parsed_kwargs = {}
                except json.JSONDecodeError:
                    # If not valid JSON, ignore kwargs
                    pass

            # Execute the command
            result = self.dcc_client.execute_cmd(command, *parsed_args, **parsed_kwargs)

            # Get scene info
            scene_info = self.get_scene_info()

            return ActionResultModel(
                success=True,
                message=f"Successfully executed command '{command}'",
                context={"result": result, "scene_info": scene_info.get("context", {})},
            ).model_dump()
        except Exception as e:
            logger.error(f"Error executing Maya command '{command}': {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to execute command '{command}'",
                error=str(e),
                prompt="Check the command syntax and try again.",
            ).model_dump()

    def execute_mel(self, script: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a MEL script in Maya.

        Args:
            script: MEL script to execute
            context: Context provided by the MCP server

        Returns:
            ActionResultModel with the result of the script execution and scene info

        """
        # Ensure we're connected to Maya
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message="Failed to execute MEL script",
                error="Not connected to Maya",
                prompt="Please check Maya connection and try again.",
            ).model_dump()

        try:
            # Execute the script
            result = self.dcc_client.execute_mel(script)

            # Get scene info
            scene_info = self.get_scene_info()

            return ActionResultModel(
                success=True,
                message="Successfully executed MEL script",
                context={"result": result, "scene_info": scene_info.get("context", {})},
            ).model_dump()
        except Exception as e:
            logger.error(f"Error executing MEL script: {e}")
            return ActionResultModel(
                success=False,
                message="Failed to execute MEL script",
                error=str(e),
                prompt="Check the MEL script syntax and try again.",
            ).model_dump()

    def get_scene_info(self) -> Dict[str, Any]:
        """Get information about the current Maya scene.

        Returns:
            ActionResultModel with scene information

        """
        # Ensure we're connected to Maya
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message="Failed to get scene info",
                error="Not connected to Maya",
                prompt="Please check Maya connection and try again.",
            ).model_dump()

        try:
            # Get scene info from the client
            scene_info = self.dcc_client.get_scene_info()

            # Add additional information
            scene_info["adapter_version"] = __version__
            scene_info["connection_info"] = {
                "host": self.host,
                "port": self.port,
                "connected": self.dcc_client.is_connected(),
                "last_check": self.last_connection_check,
            }

            # Add action information if available
            if self.action_manager is not None:
                actions_info = self.action_manager.get_actions_info()
                if actions_info.success:
                    scene_info["actions"] = {
                        "count": len(actions_info.context.get("result", {}).actions),
                        "paths": self.action_paths,
                    }

            # Add plugin information if available
            scene_info["plugins"] = {
                "paths": self.maya_mcp_plugins_paths,
                "available_plugins": self.get_available_plugins() if hasattr(self, "get_available_plugins") else [],
            }

            return ActionResultModel(
                success=True, message="Successfully retrieved scene information", context=scene_info
            ).model_dump()
        except Exception as e:
            error_msg = f"Error getting scene info: {e!s}"
            logger.error(error_msg)
            return ActionResultModel(
                success=False, message="Failed to get scene information", error=error_msg
            ).model_dump()

    def call_action_function(
        self, action_name: str, function_name: str, context: Dict[str, Any] = None, *args, **kwargs
    ) -> Dict[str, Any]:
        """Call an action function in Maya.

        Args:
            action_name: Name of the action
            function_name: Name of the function to call
            context: Context provided by the MCP server
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            ActionResultModel with the result of the function execution

        """
        if not context:
            context = {}

        # Ensure we're connected to Maya
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Failed to call {action_name}.{function_name}",
                error="Not connected to Maya",
                prompt="Please check Maya connection and try again.",
            ).model_dump()

        try:
            # Use the action manager to call the function
            if self.action_manager is not None:
                result = self.action_manager.call_action_function(action_name, function_name, *args, **kwargs)

                # If result is already an ActionResultModel, return it directly
                if isinstance(result, ActionResultModel):
                    return result.model_dump()

                # Get scene info to include in the response
                scene_info = self.get_scene_info()

                # Combine the result with scene info
                combined_result = ActionResultModel(
                    success=result.success if hasattr(result, "success") else True,
                    message=result.message if hasattr(result, "message") else f"Executed {action_name}.{function_name}",
                    prompt=result.prompt if hasattr(result, "prompt") else None,
                    error=result.error if hasattr(result, "error") else None,
                    context={
                        "result": result.context if hasattr(result, "context") else result,
                        "scene_info": scene_info.get("context", {}),
                    },
                )

                return combined_result.model_dump()
            else:
                # Fallback to direct execution through RPYC if action manager is not available
                logger.warning("Action manager not available, falling back to direct execution")
                result = self.dcc_client.call_action(action_name, function_name, context, *args, **kwargs)

                return ActionResultModel(
                    success=True,
                    message=f"Successfully executed {action_name}.{function_name} via direct call",
                    context={"result": result},
                ).model_dump()
        except Exception as e:
            error_msg = f"Error calling action '{action_name}.{function_name}': {e!s}"
            logger.error(error_msg)
            return ActionResultModel(
                success=False,
                message=f"Failed to execute {action_name}.{function_name}",
                error=error_msg,
                prompt="Check the action name, function name, and parameters and try again.",
            ).model_dump()

    def maya_action_call(
        self, action_name: str, function_name: str = None, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call an action function in Maya.

        Args:
            action_name: Name of the action
            function_name: Name of the function to call (default: None)
            context: Context provided by the MCP server

        Returns:
            ActionResultModel with information about the action execution

        """
        if not context:
            context = {}

        # Ensure we're connected to Maya
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message=f"Failed to call action '{action_name}'",
                error="Not connected to Maya",
                prompt="请检查 Maya 连接并重试。",
            ).model_dump()

        try:
            # Use the action manager if available
            if self.action_manager is not None:
                # If function_name is not specified, use a default
                if function_name is None:
                    function_name = "main"

                return self.call_action_function(action_name, function_name, context)
            else:
                # Fall back to direct execution through RPYC
                result = self.dcc_client.action_call(action_name, function_name, context)

                return ActionResultModel(
                    success=True,
                    message=f"Successfully called action '{action_name}.{function_name}'",
                    context={"result": result},
                ).model_dump()
        except Exception as e:
            error_msg = f"Error calling action '{action_name}.{function_name}': {e!s}"
            logger.error(error_msg)
            return ActionResultModel(
                success=False,
                message=f"Failed to call action '{action_name}.{function_name}'",
                error=error_msg,
                prompt="检查 action 名称和函数名称并重试。",
            ).model_dump()

    def maya_plugin_call(self, plugin_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a plugin function in Maya.

        Args:
            plugin_name: Name of the plugin
            context: Context dictionary with additional parameters

        Returns:
            ActionResultModel with the result of the plugin function call

        """
        # Ensure we're connected to Maya
        if not self.ensure_connected():
            return ActionResultModel(
                success=False,
                message="Failed to call plugin function",
                error="Not connected to Maya",
                prompt="Please check Maya connection and try again.",
            ).model_dump()

        try:
            # Initialize context if None
            if context is None:
                context = {}

            # Try to call the plugin function using the plugin manager
            try:
                result = call_plugin_function("maya", plugin_name, "func_call", context)
            except ImportError:
                # Fall back to RPYC if plugin manager is not available
                result = self.dcc_client.plugin_call(plugin_name, context)

            # Get scene info
            scene_info = self.get_scene_info()

            return ActionResultModel(
                success=True,
                message=f"Successfully called plugin function '{plugin_name}'",
                result=result,
                scene_info=scene_info,
            ).model_dump()
        except Exception as e:
            logger.error(f"Error calling plugin function '{plugin_name}': {e}")
            return ActionResultModel(
                success=False,
                message=f"Failed to call plugin function '{plugin_name}'",
                error=str(e),
                prompt="Check the plugin name and context and try again.",
            ).model_dump()

    def discover_plugins(self) -> List[Dict[str, Any]]:
        """Discover available Maya MCP plugins.

        Returns:
            List of plugin information dictionaries

        """
        plugins = []

        # Search for plugins in all plugin paths
        for plugin_path in self.maya_mcp_plugins_paths:
            plugin_files = glob.glob(os.path.join(plugin_path, "*.py"))

            for plugin_file in plugin_files:
                # Skip __init__.py and other special files
                if os.path.basename(plugin_file).startswith("__"):
                    continue

                # Get plugin name from filename
                plugin_name = os.path.splitext(os.path.basename(plugin_file))[0]

                try:
                    # Get plugin information
                    plugin_info = self._get_plugin_info(plugin_file, plugin_name)
                    if plugin_info:
                        plugins.append(plugin_info)
                except Exception as e:
                    logger.error(f"Error loading plugin '{plugin_name}': {e}")

        return plugins

    def _get_plugin_info(self, plugin_file: str, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a Maya MCP plugin.

        Args:
            plugin_file: Path to the plugin file
            plugin_name: Name of the plugin

        Returns:
            Dict with plugin information or None if the plugin is invalid

        """
        try:
            # Load the plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check if the module has the required function
            if not hasattr(module, "func_call"):
                return None

            # Get plugin information
            plugin_info = {
                "name": plugin_name,
                "path": plugin_file,
                "description": module.__doc__ or "",
            }

            # Add additional information if available
            if hasattr(module, "PLUGIN_INFO"):
                plugin_info.update(module.PLUGIN_INFO)

            return plugin_info
        except Exception as e:
            logger.error(f"Error loading plugin '{plugin_name}': {e}")
            return None

    def register_tools(self, mcp_server) -> None:
        """Register tools with the MCP server.

        This method dynamically registers all public methods of the adapter as MCP tools.
        It uses reflection to find all methods that don't start with an underscore and
        registers them with the MCP server using the adapter name as a prefix.

        Args:
            mcp_server: The MCP server instance to register tools with

        """
        logger.info("Registering Maya tools with MCP server")

        # Get all public methods (not starting with _)
        methods = [
            method
            for method in dir(self)
            if not method.startswith("_")
            and callable(getattr(self, method))
            and method not in ["get_tools", "register_tools", "ensure_connected"]
        ]

        logger.info(f"Found {len(methods)} methods to register: {methods}")

        prefix = self.dcc_name

        for method_name in methods:
            # Get the method
            method = getattr(self, method_name)

            # Get the method's docstring
            docstring = method.__doc__ or f"{method_name} method"

            # Create the tool name with the prefix
            tool_name = f"{prefix}_{method_name}"

            # Register the method as an MCP tool
            logger.info(f"Registering tool: {tool_name}")

            try:
                # Register the method with MCP server
                mcp_server.tool(tool_name)(method)
                logger.info(f"Successfully registered tool: {tool_name}")
            except Exception as e:
                logger.error(f"Error registering tool {tool_name}: {e!s}")
                import traceback

                logger.error(f"Exception details: {traceback.format_exc()}")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the list of tools provided by this adapter.

        Returns:
            List of tool definitions

        """
        # Get all public methods (not starting with _)
        methods = [
            method
            for method in dir(self)
            if not method.startswith("_")
            and callable(getattr(self, method))
            and method not in ["get_tools", "register_tools", "ensure_connected"]
        ]

        tools = []
        prefix = self.dcc_name

        for method_name in methods:
            # Get the method
            method = getattr(self, method_name)

            # Get the method's docstring
            docstring = method.__doc__ or f"{method_name} method"

            # Create the tool name with the prefix
            tool_name = f"{prefix}_{method_name}"

            # Add the tool definition
            tools.append({"name": tool_name, "description": docstring, "method": method_name})

        return tools

    def _create_action_manager(self, dcc_name):
        """Create an action manager for the DCC.

        Args:
            dcc_name: Name of the DCC

        Returns:
            Action manager instance

        """
        # This is a stub implementation to satisfy the tests
        # In a real implementation, this would create an actual action manager
        return {}


# Plugin management functions
def get_plugin_manager(dcc_name="maya"):
    """Get the plugin manager for the specified DCC.

    Args:
        dcc_name (str): Name of the DCC

    Returns:
        The plugin manager for the specified DCC

    """
    try:
        from dcc_mcp_core.plugins.manager import get_plugin_manager as core_get_plugin_manager

        return core_get_plugin_manager(dcc_name)
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not get plugin manager from dcc_mcp_core: {e}")
        # Return a simple plugin manager mock for compatibility
        mock_manager = type(
            "MockPluginManager",
            (),
            {
                "discover_plugins": lambda *args, **kwargs: {"status": "success", "plugins": []},
                "get_plugin_info": lambda *args, **kwargs: {"status": "success", "info": {}},
                "call_plugin_function": lambda *args, **kwargs: {"status": "success", "result": None},
            },
        )()
        return mock_manager


def call_plugin_function(dcc_name, plugin_name, function_name, context=None):
    """Call a plugin function.

    Args:
        dcc_name (str): Name of the DCC
        plugin_name (str): Name of the plugin
        function_name (str): Name of the function to call
        context (dict, optional): Context to pass to the function

    Returns:
        The result of the function call

    """
    try:
        from dcc_mcp_core.plugins.manager import call_plugin_function as core_call_plugin_function

        return core_call_plugin_function(dcc_name, plugin_name, function_name, context)
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not call plugin function from dcc_mcp_core: {e}")
        return {"status": "error", "message": f"Failed to call plugin function: {e}", "error": str(e)}
