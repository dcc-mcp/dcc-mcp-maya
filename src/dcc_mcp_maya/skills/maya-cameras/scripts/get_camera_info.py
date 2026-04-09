"""Query detailed information about a camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_camera_info(camera_name: str) -> dict:
    """Query detailed information about a camera.

    Args:
        camera_name: Transform or shape name of the camera.

    Returns:
        ActionResultModel dict with ``context`` containing focal_length,
        near/far clip, position, rotation, renderable, and field of view.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return error_result("Camera not found: {}".format(camera_name)).to_dict()

        shapes = cmds.listRelatives(camera_name, shapes=True) or []
        if not shapes:
            # camera_name might already be a shape
            if cmds.objectType(camera_name) == "camera":
                shape = camera_name
                transform_list = cmds.listRelatives(camera_name, parent=True) or [camera_name]
                transform = transform_list[0]
            else:
                return error_result("'{}' is not a camera".format(camera_name)).to_dict()
        else:
            shape = shapes[0]
            transform = camera_name

        info = {
            "name": transform,
            "shape": shape,
        }

        for attr in ("focalLength", "nearClipPlane", "farClipPlane", "renderable"):
            try:
                info[attr] = cmds.getAttr("{}.{}".format(shape, attr))
            except Exception:
                info[attr] = None

        for axis_attr in ("translate", "rotate"):
            try:
                raw = cmds.getAttr("{}.{}".format(transform, axis_attr))
                info[axis_attr] = list(raw[0]) if raw else [0.0, 0.0, 0.0]
            except Exception:
                info[axis_attr] = [0.0, 0.0, 0.0]

        return success_result("Camera info for '{}'".format(transform), **info).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_camera_info failed")
        return error_result("Failed to get camera info", str(exc)).to_dict()



def main(**kwargs):
    return get_camera_info(**kwargs)


if __name__ == "__main__":
    import json
    result = get_camera_info()
    print(json.dumps(result))
