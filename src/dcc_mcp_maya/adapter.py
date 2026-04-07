"""Maya MCP adapter for external clients (runs outside Maya).

This module provides MayaAdapter, which inherits from DCCAdapter (dcc-mcp-ipc)
and connects to the MayaRPyCService running inside Maya via RPyC.
"""

# Import built-in modules
import logging
from typing import Any
from typing import Optional

# Import third-party modules
from dcc_mcp_core import ActionResultModel

# Import local modules
from dcc_mcp_ipc.adapter.dcc import DCCAdapter

# Configure logging
logger = logging.getLogger(__name__)


class MayaAdapter(DCCAdapter):
    """Adapter for connecting to Maya via the dcc-mcp-ipc layer.

    This adapter extends DCCAdapter to provide Maya-specific convenience methods.
    It communicates with the MayaRPyCService running inside Maya via RPyC.

    Usage:
        adapter = MayaAdapter()
        result = adapter.get_scene_info()
        result = adapter.execute_mel("polySphere -r 1;")
        result = adapter.create_primitive("sphere", radius=2.0)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        connection_timeout: float = 5.0,
    ):
        """Initialize the Maya adapter.

        Args:
            host: Maya RPyC server host. Defaults to localhost via service discovery.
            port: Maya RPyC server port. Defaults to auto-discovery.
            connection_timeout: Seconds to wait for connection.

        """
        super().__init__(
            dcc_name="maya",
            host=host,
            port=port,
            connection_timeout=connection_timeout,
        )

    def _initialize_action_paths(self) -> None:
        """Initialize action search paths for Maya.

        Maya built-in actions live inside the dcc_mcp_maya package.
        Additional paths can be registered via MAYA_MCP_ACTION_PATHS env var.
        """
        import os
        import dcc_mcp_maya.actions as _pkg
        builtin_actions_dir = os.path.dirname(_pkg.__file__)
        if os.path.isdir(builtin_actions_dir):
            self._action_paths.append(builtin_actions_dir)

        env_paths = os.environ.get("MAYA_MCP_ACTION_PATHS", "")
        for path in env_paths.split(os.pathsep):
            path = path.strip()
            if path and os.path.isdir(path):
                self._action_paths.append(path)

    def get_application_info(self) -> dict[str, Any]:
        """Get Maya application info from the remote service."""
        if not self._ensure_connected():
            return {"error": "Not connected to Maya"}
        try:
            return dict(self.client.root.get_application_info())
        except Exception as e:
            logger.error(f"Failed to get application info: {e}")
            return {"error": str(e)}

    def get_application_info(self) -> dict[str, Any]:
        """Get Maya application info from the remote service."""
        if not self._ensure_connected():
            return {"error": "Not connected to Maya"}
        try:
            return dict(self.client.root.get_application_info())
        except Exception as e:
            logger.error(f"Failed to get application info: {e}")
            return {"error": str(e)}

    # ── Maya-specific convenience methods ──

    def execute_mel(self, script: str) -> ActionResultModel:
        """Execute a MEL script in Maya.

        Args:
            script: MEL script to execute.

        Returns:
            ActionResultModel with execution result.

        """
        if not self._ensure_connected():
            return ActionResultModel(
                success=False,
                message="Not connected to Maya",
                error="ConnectionError",
            )
        try:
            result = self.client.root.execute_mel(script)
            return ActionResultModel(
                success=True,
                message="MEL script executed successfully",
                context={"result": result},
            )
        except Exception as e:
            logger.error(f"MEL execution failed: {e}")
            return ActionResultModel(success=False, message=str(e), error=str(e))

    def execute_maya_cmd(self, command: str, *args, **kwargs) -> ActionResultModel:
        """Execute a Maya cmds command.

        Args:
            command: Name of the maya.cmds function (e.g. "polySphere").
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            ActionResultModel with execution result.

        """
        if not self._ensure_connected():
            return ActionResultModel(
                success=False,
                message="Not connected to Maya",
                error="ConnectionError",
            )
        try:
            result = self.client.root.execute_maya_cmd(command, *args, **kwargs)
            return ActionResultModel(
                success=True,
                message=f"Command '{command}' executed successfully",
                context={"result": result},
            )
        except Exception as e:
            logger.error(f"Maya command '{command}' failed: {e}")
            return ActionResultModel(success=False, message=str(e), error=str(e))

    def get_scene_info(self) -> ActionResultModel:
        """Get current Maya scene information.

        Returns:
            ActionResultModel with scene details.

        """
        if not self._ensure_connected():
            return ActionResultModel(
                success=False,
                message="Not connected to Maya",
                error="ConnectionError",
            )
        try:
            info = dict(self.client.root.get_scene_info())
            return ActionResultModel(
                success=True,
                message="Scene info retrieved",
                context=info,
            )
        except Exception as e:
            logger.error(f"Failed to get scene info: {e}")
            return ActionResultModel(success=False, message=str(e), error=str(e))

    def get_session_info(self) -> ActionResultModel:
        """Get current Maya session information.

        Returns:
            ActionResultModel with session details.

        """
        if not self._ensure_connected():
            return ActionResultModel(
                success=False,
                message="Not connected to Maya",
                error="ConnectionError",
            )
        try:
            info = dict(self.client.root.get_session_info())
            return ActionResultModel(
                success=True,
                message="Session info retrieved",
                context=info,
            )
        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return ActionResultModel(success=False, message=str(e), error=str(e))

    def create_primitive(self, primitive_type: str, **kwargs) -> ActionResultModel:
        """Create a Maya primitive.

        Args:
            primitive_type: "sphere", "cube", "cylinder", "cone", "plane", "torus".
            **kwargs: Additional parameters (e.g. radius, width, height).

        Returns:
            ActionResultModel with created object info.

        """
        if not self._ensure_connected():
            return ActionResultModel(
                success=False,
                message="Not connected to Maya",
                error="ConnectionError",
            )
        try:
            result = dict(self.client.root.create_primitive(primitive_type, **kwargs))
            return ActionResultModel(
                success=True,
                message=f"Created {primitive_type} successfully",
                context=result,
            )
        except Exception as e:
            logger.error(f"Failed to create primitive '{primitive_type}': {e}")
            return ActionResultModel(success=False, message=str(e), error=str(e))

    def list_actions(self) -> ActionResultModel:
        """List all available actions registered in the Maya service.

        Returns:
            ActionResultModel with actions dict.

        """
        if not self._ensure_connected():
            return ActionResultModel(
                success=False,
                message="Not connected to Maya",
                error="ConnectionError",
            )
        try:
            data = dict(self.client.root.list_actions())
            return ActionResultModel(
                success=True,
                message="Actions listed successfully",
                context=data,
            )
        except Exception as e:
            logger.error(f"Failed to list actions: {e}")
            return ActionResultModel(success=False, message=str(e), error=str(e))

    def call_action(self, action_name: str, **kwargs) -> ActionResultModel:
        """Call an action registered in the Maya service.

        Args:
            action_name: Name of the action to call.
            **kwargs: Arguments passed to the action.

        Returns:
            ActionResultModel with action result.

        """
        if not self._ensure_connected():
            return ActionResultModel(
                success=False,
                message="Not connected to Maya",
                error="ConnectionError",
            )
        try:
            result = self.client.root.call_action(action_name, **kwargs)
            if isinstance(result, dict):
                return ActionResultModel(**result)
            return ActionResultModel(
                success=True,
                message=f"Action '{action_name}' executed",
                context={"result": result},
            )
        except Exception as e:
            logger.error(f"Failed to call action '{action_name}': {e}")
            return ActionResultModel(success=False, message=str(e), error=str(e))

    def _ensure_connected(self) -> bool:
        """Ensure the client is connected to Maya.

        Returns:
            True if connected, False otherwise.

        """
        if self.client is None:
            self._initialize_client()
        if self.client is None:
            return False
        try:
            return self.client.is_connected()
        except Exception:
            return False
