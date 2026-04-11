"""List all cameras in the scene with their basic attributes."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def list_cameras(include_default: bool = True) -> dict:
    """List all cameras in the scene with their basic attributes.

    Args:
        include_default: If True (default), includes Maya's built-in cameras
            (``persp``, ``top``, ``front``, ``side``).  Set to False to return
            only user-created cameras.

    Returns:
        ActionResultModel dict with ``context.cameras`` (list of dicts) and
        ``context.count``.
    """

    _DEFAULT_CAMERAS = {"persp", "top", "front", "side", "perspShape", "topShape", "frontShape", "sideShape"}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        camera_shapes = cmds.ls(type="camera") or []
        cameras = []
        for shape in camera_shapes:
            transform = (cmds.listRelatives(shape, parent=True) or [shape])[0]
            if not include_default and transform in _DEFAULT_CAMERAS:
                continue
            cam = {
                "name": transform,
                "shape": shape,
                "focal_length": cmds.getAttr("{}.focalLength".format(shape)),
                "near_clip": cmds.getAttr("{}.nearClipPlane".format(shape)),
                "far_clip": cmds.getAttr("{}.farClipPlane".format(shape)),
                "renderable": cmds.getAttr("{}.renderable".format(shape)),
            }
            cameras.append(cam)

        return skill_success(
            "Found {} camera(s)".format(len(cameras)),
            cameras=cameras,
            count=len(cameras),
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list cameras")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_cameras`."""
    return list_cameras(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
