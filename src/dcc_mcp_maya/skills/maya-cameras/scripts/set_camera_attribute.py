"""Set an attribute on a camera shape or transform."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def set_camera_attribute(
    camera_name: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute on a camera shape or transform.

    Common camera shape attributes: ``"focalLength"``, ``"nearClipPlane"``,
    ``"farClipPlane"``, ``"horizontalFieldOfView"``, ``"verticalFieldOfView"``,
    ``"renderable"``, ``"filmFit"``.

    Args:
        camera_name: Transform or shape name of the camera.
        attribute: Attribute name.
        value: New value.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return error_result("Camera not found: {}".format(camera_name)).to_dict()

        shapes = cmds.listRelatives(camera_name, shapes=True) or []
        shape = shapes[0] if shapes else camera_name

        full_attr = "{}.{}".format(shape, attribute)
        if not cmds.objExists(full_attr):
            full_attr = "{}.{}".format(camera_name, attribute)
        if not cmds.objExists(full_attr):
            return error_result("Attribute '{}' not found on camera '{}'".format(attribute, camera_name)).to_dict()

        if isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        elif isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(full_attr, value[0], value[1], value[2], type="double3")
        else:
            cmds.setAttr(full_attr, value)

        return success_result(
            "Set {}.{} = {}".format(camera_name, attribute, value),
            camera_name=camera_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_camera_attribute failed")
        return error_result("Failed to set camera attribute", str(exc)).to_dict()



def main(**kwargs):
    return set_camera_attribute(**kwargs)


if __name__ == "__main__":
    import json
    result = set_camera_attribute()
    print(json.dumps(result))
