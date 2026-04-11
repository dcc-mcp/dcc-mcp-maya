"""Get information about a Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def get_camera_info(camera_name: str) -> dict:
    """Return settings for a Maya camera.

    Args:
        camera_name: Name of the camera transform or shape node.

    Returns:
        ActionResultModel dict with focal length, clipping planes, aperture, etc.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return maya_error(
                "Camera not found: {}".format(camera_name),
                "'{}' does not exist".format(camera_name),
            )

        node_type = cmds.objectType(camera_name)
        if node_type == "transform":
            shapes = cmds.listRelatives(camera_name, shapes=True, type="camera") or []
            if not shapes:
                return maya_error(
                    "No camera shape under '{}'".format(camera_name),
                    "Transform has no camera shape",
                )
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

        return maya_success(
            "Camera info for '{}'".format(cam_node),
            prompt="Use set_camera_attribute to modify focal length or clipping planes.",
            **info,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get camera info for '{}'".format(camera_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_camera_info`."""
    return get_camera_info(**kwargs)

if __name__ == "__main__":
    import json

    result = get_camera_info("persp")
    print(json.dumps(result))
