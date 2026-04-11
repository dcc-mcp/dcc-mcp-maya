"""List all cameras in the scene with their basic attributes."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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

        return maya_success(
            "Found {} camera(s)".format(len(cameras)),
            cameras=cameras,
            count=len(cameras),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list cameras")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_cameras`."""
    return list_cameras(**kwargs)

if __name__ == "__main__":
    import json

    result = list_cameras()
    print(json.dumps(result))
