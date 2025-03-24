"""Scene information actions for Maya.

This module provides actions for getting information about the current Maya scene.
"""

from typing import List

from dcc_mcp_core.models import ActionResultModel


def get_scene_info(**kwargs) -> ActionResultModel:
    """Get information about the current Maya scene.

    Returns:
        ActionResultModel with scene information

    """
    # Get Maya commands from context
    maya_client = kwargs.pop("_maya_rpyc_client", None)
    cmds = kwargs.pop("_maya_cmds", None)

    if not cmds:
        return ActionResultModel(
            success=False,
            message="get_scene_info failed",
            error="Maya commands not available",
            prompt="Please ensure Maya is running and connected",
            context={},
        )

    try:
        # Get scene path
        scene_path = cmds.file(query=True, sceneName=True) or ""

        # Get selection
        selection = cmds.ls(selection=True) or []

        # Get all objects in the scene
        all_objects = cmds.ls(long=True) or []

        # Get all cameras
        cameras = cmds.ls(cameras=True) or []

        # Get all lights
        lights = cmds.ls(lights=True) or []

        # Get all meshes
        meshes = cmds.ls(type="mesh") or []

        # Get scene stats
        stats = {
            "num_objects": len(all_objects),
            "num_selected": len(selection),
            "num_cameras": len(cameras),
            "num_lights": len(lights),
            "num_meshes": len(meshes),
        }

        # Return success result
        return ActionResultModel(
            success=True,
            message="get_scene_info success",
            prompt="可以使用 select_objects 函数选择场景中的对象"
            if meshes
            else "场景中没有网格对象，可以使用 create_primitive 函数创建几何体",
            error=None,
            context={
                "scene_path": scene_path,
                "selection": selection,
                "stats": stats,
                "cameras": cameras,
                "lights": lights,
                "meshes": meshes[:50],  # Limit to first 50 meshes to avoid too much data
                "has_more_meshes": len(meshes) > 50,
            },
        )
    except Exception as e:
        # Return error result
        return ActionResultModel(
            success=False,
            message="get_scene_info failed",
            error=str(e),
            prompt="Please check Maya is running and connected",
            context={},
        )


def select_objects(object_names: List[str], **kwargs) -> ActionResultModel:
    """Select objects in Maya.

    Args:
        object_names: List of object names to select

    Returns:
        ActionResultModel with the result of the selection

    """
    # Get Maya commands from context
    maya_client = kwargs.pop("_maya_rpyc_client", None)
    cmds = kwargs.pop("_maya_cmds", None)

    if not cmds:
        return ActionResultModel(
            success=False,
            message="select_objects failed",
            error="Maya commands not available",
            prompt="Please ensure Maya is running and connected",
            context={},
        )

    if not object_names:
        return ActionResultModel(
            success=False,
            message="select_objects failed",
            error="No object names provided",
            prompt="Please provide a list of object names to select",
            context={},
        )

    try:
        # Clear current selection
        cmds.select(clear=True)

        # Select objects one by one, ignoring any that don't exist
        selected = []
        not_found = []

        for obj_name in object_names:
            try:
                if cmds.objExists(obj_name):
                    cmds.select(obj_name, add=True)
                    selected.append(obj_name)
                else:
                    not_found.append(obj_name)
            except Exception:
                not_found.append(obj_name)

        # Return success result
        if selected:
            return ActionResultModel(
                success=True,
                message=f"select_objects success, selected {len(selected)} objects"
                + (f", {len(not_found)} objects not found" if not_found else ""),
                prompt="可以使用 get_scene_info 函数获取更多关于选择对象的信息",
                error=None,
                context={"selected": selected, "not_found": not_found},
            )
        else:
            return ActionResultModel(
                success=False,
                message="select_objects failed, no objects selected",
                error="None of the specified objects exist",
                prompt="Please check object names or use get_scene_info to get object list",
                context={"not_found": not_found},
            )
    except Exception as e:
        # Return error result
        return ActionResultModel(
            success=False,
            message="select_objects failed",
            error=str(e),
            prompt="Please check object names or view Maya console for more information",
            context={"attempted_objects": object_names},
        )
