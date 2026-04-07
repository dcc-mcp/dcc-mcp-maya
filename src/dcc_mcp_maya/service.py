"""Maya RPyC service running inside Maya's Python interpreter.

This service is loaded as part of the Maya plugin and exposes Maya functionality
to external clients via RPyC. It inherits from DCCRPyCService (dcc-mcp-ipc) and
implements all Maya-specific abstract methods.
"""

# Import built-in modules
import logging
import sys
from typing import Any
from typing import Optional

# Import third-party modules
from dcc_mcp_core import ActionResultModel
from dcc_mcp_core import ActionRegistry

# Import local modules
from dcc_mcp_ipc.server.dcc import DCCRPyCService

# Configure logging
logger = logging.getLogger(__name__)


class MayaRPyCService(DCCRPyCService):
    """RPyC service that runs inside Maya and exposes Maya functionality.

    This service implements the DCCRPyCService interface, providing Maya-specific
    implementations for scene management, session info, and primitive creation.
    It also supports the action system from dcc-mcp-core for extensible Maya commands.
    """

    def __init__(self):
        """Initialize the Maya RPyC service."""
        super().__init__()
        self._action_registry = ActionRegistry()
        self._discover_builtin_actions()

    def _discover_builtin_actions(self):
        """Auto-discover and register built-in Maya actions."""
        try:
            from dcc_mcp_maya import actions as _actions_pkg
            import importlib
            import pkgutil
            pkg_path = _actions_pkg.__path__
            for _importer, module_name, _ispkg in pkgutil.iter_modules(pkg_path):
                try:
                    mod = importlib.import_module(f"dcc_mcp_maya.actions.{module_name}")
                    if hasattr(mod, "register_actions"):
                        mod.register_actions(self._action_registry)
                except Exception as e:
                    logger.warning(f"Failed to load action module {module_name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to discover built-in actions: {e}")

    # ── ApplicationRPyCService abstract methods ──

    def get_application_info(self) -> dict[str, Any]:
        """Get Maya application information."""
        try:
            import maya.cmds as cmds
            return {
                "name": "Maya",
                "version": cmds.about(version=True),
                "api_version": cmds.about(apiVersion=True),
                "os": cmds.about(os=True),
                "python_version": sys.version,
            }
        except Exception as e:
            logger.error(f"Failed to get Maya application info: {e}")
            return {"name": "Maya", "error": str(e)}

    def get_environment_info(self) -> dict[str, Any]:
        """Get the Python environment info inside Maya."""
        try:
            import maya.cmds as cmds
            return {
                "python_version": sys.version,
                "python_executable": sys.executable,
                "maya_version": cmds.about(version=True),
                "sys_path": sys.path,
            }
        except Exception as e:
            return {"python_version": sys.version, "error": str(e)}

    def execute_python(self, code: str, context: Optional[dict[str, Any]] = None) -> Any:
        """Execute Python code inside Maya."""
        exec_globals = {"__builtins__": __builtins__}
        if context:
            exec_globals.update(context)

        exec_locals: dict[str, Any] = {}
        exec(code, exec_globals, exec_locals)  # noqa: S102

        # Return 'result' if defined, otherwise return all locals
        if "result" in exec_locals:
            return exec_locals["result"]
        return exec_locals

    def import_module(self, module_name: str) -> Any:
        """Import a module in Maya's Python environment."""
        import importlib
        return importlib.import_module(module_name)

    def call_function(self, module_name: str, function_name: str, *args, **kwargs) -> Any:
        """Call a function from a module in Maya's Python environment."""
        import importlib
        mod = importlib.import_module(module_name)
        func = getattr(mod, function_name)
        return func(*args, **kwargs)

    # ── DCCRPyCService abstract methods ──

    def get_scene_info(self) -> dict[str, Any]:
        """Get information about the current Maya scene."""
        try:
            import maya.cmds as cmds
            scene_path = cmds.file(q=True, sceneName=True) or ""
            import os
            return {
                "path": scene_path,
                "name": os.path.basename(scene_path) if scene_path else "untitled",
                "modified": cmds.file(q=True, modified=True),
                "selection": cmds.ls(selection=True) or [],
                "object_count": len(cmds.ls(dag=True, transforms=True) or []),
            }
        except Exception as e:
            logger.error(f"Failed to get scene info: {e}")
            return {"error": str(e)}

    def get_session_info(self) -> dict[str, Any]:
        """Get information about the current Maya session."""
        try:
            import maya.cmds as cmds
            return {
                "version": cmds.about(version=True),
                "api_version": cmds.about(apiVersion=True),
                "os": cmds.about(os=True),
                "project": cmds.workspace(q=True, rootDirectory=True),
                "python_version": sys.version,
            }
        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return {"error": str(e)}

    def create_primitive(self, primitive_type: str, **kwargs) -> Any:
        """Create a Maya primitive object."""
        import maya.cmds as cmds
        primitive_map = {
            "sphere": lambda **kw: cmds.polySphere(**kw),
            "cube": lambda **kw: cmds.polyCube(**kw),
            "cylinder": lambda **kw: cmds.polyCylinder(**kw),
            "cone": lambda **kw: cmds.polyCone(**kw),
            "plane": lambda **kw: cmds.polyPlane(**kw),
            "torus": lambda **kw: cmds.polyTorus(**kw),
        }
        key = primitive_type.lower()
        if key not in primitive_map:
            raise ValueError(f"Unknown primitive type '{primitive_type}'. Available: {list(primitive_map)}")
        result = primitive_map[key](**kwargs)
        return {"created": result, "type": primitive_type}

    # ── Maya-specific exposed methods ──

    def exposed_execute_mel(self, script: str) -> Any:
        """Execute a MEL script inside Maya.

        Args:
            script: MEL script string to execute.

        Returns:
            Result of the MEL execution.

        """
        import maya.mel as mel
        return mel.eval(script)

    def exposed_execute_maya_cmd(self, command: str, *args, **kwargs) -> Any:
        """Execute a Maya Python command (cmds.xxx).

        Args:
            command: Name of the maya.cmds function.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Result of the command.

        """
        import maya.cmds as cmds
        func = getattr(cmds, command)
        return func(*args, **kwargs)

    def exposed_get_scene_info(self) -> dict[str, Any]:
        """Expose get_scene_info via RPyC."""
        return self.get_scene_info()

    def exposed_get_session_info(self) -> dict[str, Any]:
        """Expose get_session_info via RPyC."""
        return self.get_session_info()

    def exposed_get_application_info(self) -> dict[str, Any]:
        """Expose get_application_info via RPyC."""
        return self.get_application_info()

    def exposed_list_actions(self) -> dict[str, Any]:
        """List all registered Maya actions."""
        try:
            actions = self._action_registry.list_actions()
            return {"actions": actions}
        except Exception as e:
            logger.error(f"Failed to list actions: {e}")
            return {"actions": {}, "error": str(e)}

    def exposed_call_action(self, action_name: str, **kwargs) -> Any:
        """Call a registered Maya action by name.

        Args:
            action_name: Name of the action to call.
            **kwargs: Arguments for the action.

        Returns:
            ActionResultModel serialized as dict.

        """
        try:
            result = self._action_registry.call_action(action_name, **kwargs)
            if isinstance(result, ActionResultModel):
                return result.model_dump()
            return result
        except Exception as e:
            logger.error(f"Failed to call action '{action_name}': {e}")
            return ActionResultModel(
                success=False,
                message=f"Action '{action_name}' failed: {e}",
                error=str(e),
            ).model_dump()
