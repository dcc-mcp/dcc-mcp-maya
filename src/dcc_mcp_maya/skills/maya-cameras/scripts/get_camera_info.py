"""Get information about a Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_camera_info(camera_name: str) -> dict:
    """Return settings for a Maya camera.

    Args:
        camera_name: Name of the camera transform or shape node.

    Returns:
        ActionResultModel dict with focal length, clipping planes, aperture, etc.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return error_result(
                "Camera not found: {}".format(camera_name),
                "'{}' does not exist".format(camera_name),
            ).to_dict()

        node_type = cmds.objectType(camera_name)
        if node_type == "transform":
            shapes = cmds.listRelatives(camera_name, shapes=True, type="camera") or []
            if not shapes:
                return error_result(
                    "No camera shape under '{}'".format(camera_name),
                    "Transform has no camera shape",
                ).to_dict()
            cam_node = shapes[0]
            transform = camera_name
        else:
            cam_node = camera_name
            parents = cmds.listRelatives(camera_name, parent=True) or []
            transform = parents[0] if parents else camera_name

        info = {
            "transform": transform,
            "shape": cam_node,
            "focal_length": cmds.getAttr("{}.focalLength".format(cam_node)),
            "near_clip": cmds.getAttr("{}.nearClipPlane".format(cam_node)),
            "far_clip": cmds.getAttr("{}.farClipPlane".format(cam_node)),
            "horizontal_aperture": cmds.getAttr("{}.horizontalFilmAperture".format(cam_node)),
            "vertical_aperture": cmds.getAttr("{}.verticalFilmAperture".format(cam_node)),
            "translate": list(cmds.getAttr("{}.translate".format(transform))[0]),
            "rotate": list(cmds.getAttr("{}.rotate".format(transform))[0]),
        }

        return success_result(
            "Camera info for '{}'".format(cam_node),
            prompt="Use set_camera_attribute to modify focal length or clipping planes.",
            **info,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_camera_info failed")
        return error_result("Failed to get camera info for '{}'".format(camera_name), str(exc)).to_dict()


def main(**kwargs):
    return get_camera_info(**kwargs)


if __name__ == "__main__":
    import json

    result = get_camera_info("persp")
    print(json.dumps(result))
