"""Maya scene management actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def new_scene(force: bool = False) -> dict:
    """Create a new Maya scene.

    Args:
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(new=True, force=force)
        return success_result("New scene created").to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("new_scene failed")
        return error_result("Failed to create new scene", str(exc)).to_dict()


def save_scene(file_path: Optional[str] = None, file_type: str = "mayaBinary") -> dict:
    """Save the current Maya scene.

    Args:
        file_path: Destination path.  If None, saves to the current file path.
        file_type: ``"mayaBinary"`` (default) or ``"mayaAscii"``.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if file_path:
            cmds.file(rename=file_path)
        saved = cmds.file(save=True, type=file_type)
        return success_result(
            f"Scene saved to {saved}",
            file_path=saved,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("save_scene failed")
        return error_result("Failed to save scene", str(exc)).to_dict()


def open_scene(file_path: str, force: bool = False) -> dict:
    """Open a Maya scene file.

    Args:
        file_path: Path to the .ma / .mb file.
        force: If True, discard unsaved changes without prompting.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.file(file_path, open=True, force=force)
        return success_result(
            f"Opened scene: {file_path}",
            file_path=file_path,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("open_scene failed")
        return error_result(f"Failed to open {file_path}", str(exc)).to_dict()


def list_objects(object_type: Optional[str] = None, dag: bool = True) -> dict:
    """List objects in the current Maya scene.

    Args:
        object_type: Optional Maya type filter (e.g. ``"mesh"``, ``"transform"``).
        dag: If True, only return DAG nodes.

    Returns:
        ActionResultModel dict with ``context.objects`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"dag": dag}
        if object_type:
            kwargs["type"] = object_type
        objects = cmds.ls(**kwargs) or []
        return success_result(
            f"Found {len(objects)} objects",
            objects=objects,
            count=len(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_objects failed")
        return error_result("Failed to list objects", str(exc)).to_dict()


def get_selection() -> dict:
    """Return the current Maya selection.

    Returns:
        ActionResultModel dict with ``context.selection`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        selection = cmds.ls(selection=True) or []
        return success_result(
            f"{len(selection)} objects selected",
            selection=selection,
            count=len(selection),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_selection failed")
        return error_result("Failed to get selection", str(exc)).to_dict()


def set_selection(objects: List[str]) -> dict:
    """Set the active Maya selection.

    Args:
        objects: List of object names to select.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.select(objects, replace=True)
        return success_result(
            f"Selected {len(objects)} objects",
            selection=objects,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_selection failed")
        return error_result("Failed to set selection", str(exc)).to_dict()


def get_session_info() -> dict:
    """Return Maya version, scene path, and basic stats.

    Returns:
        ActionResultModel dict with version, scene, fps information.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        info = {
            "maya_version": cmds.about(version=True),
            "api_version": cmds.about(apiVersion=True),
            "scene_file": cmds.file(query=True, sceneName=True) or "<unsaved>",
            "scene_modified": cmds.file(query=True, modified=True),
            "fps": cmds.currentUnit(query=True, time=True),
            "up_axis": cmds.upAxis(query=True, axis=True),
            "object_count": len(cmds.ls(dag=True) or []),
        }
        return success_result("Maya session info", **info).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_session_info failed")
        return error_result("Failed to get session info", str(exc)).to_dict()
