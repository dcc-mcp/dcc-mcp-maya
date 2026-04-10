"""Query current shot metadata: frame range, active camera, scene name."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os

logger = logging.getLogger(__name__)


def get_shot_info() -> dict:
    """Query current shot metadata from the open Maya scene.

    Returns:
        ActionResultModel dict with shot metadata (frame range, camera, scene path).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        scene_path = cmds.file(q=True, sceneName=True) or ""
        scene_name = os.path.splitext(os.path.basename(scene_path))[0] if scene_path else "untitled"

        start_frame = cmds.playbackOptions(q=True, minTime=True)
        end_frame = cmds.playbackOptions(q=True, maxTime=True)
        current_frame = cmds.currentTime(q=True)

        # Get the active perspective camera
        active_cam = ""
        try:
            panels = cmds.getPanel(type="modelPanel") or []
            if panels:
                active_cam = cmds.modelEditor(panels[0], q=True, camera=True) or ""
        except Exception:
            pass

        # Collect all cameras in scene
        cam_shapes = cmds.ls(type="camera") or []
        cameras = []
        for shape in cam_shapes:
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            cameras.append(parents[0] if parents else shape)

        return success_result(
            "Shot info for '{}'".format(scene_name),
            prompt="Use export_shot_fbx or export_shot_alembic to export this shot.",
            scene_name=scene_name,
            scene_path=scene_path,
            start_frame=start_frame,
            end_frame=end_frame,
            current_frame=current_frame,
            active_camera=active_cam,
            cameras=cameras,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_shot_info failed")
        return error_result("Failed to get shot info", str(exc)).to_dict()


def main(**kwargs):
    return get_shot_info(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(get_shot_info()))
