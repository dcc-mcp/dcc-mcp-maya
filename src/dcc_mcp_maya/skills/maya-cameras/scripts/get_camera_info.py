"""Get information about a Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def get_camera_info(camera_name: str) -> dict:
    """Return settings for a Maya camera.

    Args:
        camera_name: Name of the camera transform or shape node.

    Returns:
        ActionResultModel dict with focal length, clipping planes, aperture, etc.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, camera_name)
        if err:
            return err

        node_type = cmds.objectType(camera_name)
        if node_type == "transform":
            shapes = cmds.listRelatives(camera_name, shapes=True, type="camera") or []
            if not shapes:
                return skill_error(
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

        return skill_success(
            "Camera info for '{}'".format(cam_node),
            prompt="Use set_camera_attribute to modify focal length or clipping planes.",
            **info,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get camera info for '{}'".format(camera_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_camera_info`."""
    return get_camera_info(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
