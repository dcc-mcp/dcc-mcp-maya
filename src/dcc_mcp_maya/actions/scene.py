"""Scene management actions for Maya MCP."""

# Import built-in modules
import logging
import os

# Import third-party modules
from dcc_mcp_core import ActionResultModel

logger = logging.getLogger(__name__)


def new_scene(force: bool = False) -> ActionResultModel:
    """Create a new Maya scene.

    Args:
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel indicating success or failure.

    """
    import maya.cmds as cmds
    try:
        cmds.file(new=True, force=force)
        return ActionResultModel(success=True, message="New scene created")
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def save_scene(file_path: str = "", file_type: str = "mayaBinary") -> ActionResultModel:
    """Save the current Maya scene.

    Args:
        file_path: Path to save. If empty, saves to the current scene path.
        file_type: Maya file type ("mayaBinary" or "mayaAscii").

    Returns:
        ActionResultModel with the saved file path.

    """
    import maya.cmds as cmds
    try:
        if file_path:
            saved_path = cmds.file(rename=file_path)
            cmds.file(save=True, type=file_type)
        else:
            saved_path = cmds.file(save=True, type=file_type)
        return ActionResultModel(
            success=True,
            message=f"Scene saved to {saved_path}",
            context={"path": saved_path},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def open_scene(file_path: str, force: bool = False) -> ActionResultModel:
    """Open a Maya scene file.

    Args:
        file_path: Path to the .ma or .mb file.
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel indicating success or failure.

    """
    import maya.cmds as cmds
    try:
        if not os.path.exists(file_path):
            return ActionResultModel(
                success=False,
                message=f"File not found: {file_path}",
                error="FileNotFoundError",
            )
        cmds.file(file_path, open=True, force=force)
        return ActionResultModel(
            success=True,
            message=f"Opened scene: {file_path}",
            context={"path": file_path},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def list_objects(object_type: str = "", dag: bool = True) -> ActionResultModel:
    """List objects in the current Maya scene.

    Args:
        object_type: Optional Maya object type filter (e.g. "mesh", "camera").
        dag: If True, only list DAG nodes.

    Returns:
        ActionResultModel with list of object names.

    """
    import maya.cmds as cmds
    try:
        kwargs: dict = {"dag": dag}
        if object_type:
            kwargs["type"] = object_type
        objects = cmds.ls(**kwargs) or []
        return ActionResultModel(
            success=True,
            message=f"Found {len(objects)} objects",
            context={"objects": objects, "count": len(objects)},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def get_selection() -> ActionResultModel:
    """Get the current selection in Maya.

    Returns:
        ActionResultModel with selected object names.

    """
    import maya.cmds as cmds
    try:
        selection = cmds.ls(selection=True) or []
        return ActionResultModel(
            success=True,
            message=f"Selection has {len(selection)} items",
            context={"selection": selection},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def set_selection(objects: list) -> ActionResultModel:
    """Set the selection in Maya.

    Args:
        objects: List of object names to select.

    Returns:
        ActionResultModel indicating success.

    """
    import maya.cmds as cmds
    try:
        cmds.select(objects, replace=True)
        return ActionResultModel(
            success=True,
            message=f"Selected {len(objects)} objects",
            context={"selection": objects},
        )
    except Exception as e:
        return ActionResultModel(success=False, message=str(e), error=str(e))


def register_actions(registry) -> None:
    """Register all scene actions with the given ActionRegistry.

    Args:
        registry: ActionRegistry instance from dcc-mcp-core.

    """
    for func in [new_scene, save_scene, open_scene, list_objects, get_selection, set_selection]:
        try:
            registry.register(func.__name__, func)
        except Exception as e:
            logger.warning(f"Failed to register action '{func.__name__}': {e}")
