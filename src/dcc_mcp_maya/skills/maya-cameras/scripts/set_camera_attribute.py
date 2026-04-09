"""Set an attribute on a Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_camera_attribute(camera_name: str, attribute: str, value: object) -> dict:
    """Set an attribute on a Maya camera node.

    Common attributes: ``focalLength``, ``nearClipPlane``, ``farClipPlane``,
    ``horizontalFilmAperture``, ``verticalFilmAperture``, ``fStop``.

    Args:
        camera_name: Name of the camera transform or shape node.
        attribute: Attribute name (camelCase Maya attribute).
        value: Value to set.

    Returns:
        ActionResultModel dict with ``context.camera_name`` and ``context.attribute``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return error_result(
                "Camera not found: {}".format(camera_name),
                "'{}' does not exist".format(camera_name),
            ).to_dict()

        # Resolve shape node if transform was supplied
        node_type = cmds.objectType(camera_name)
        if node_type == "transform":
            shapes = cmds.listRelatives(camera_name, shapes=True, type="camera") or []
            if not shapes:
                return error_result(
                    "No camera shape under '{}'".format(camera_name),
                    "Transform has no camera shape",
                ).to_dict()
            cam_node = shapes[0]
        else:
            cam_node = camera_name

        full_attr = "{}.{}".format(cam_node, attribute)
        cmds.setAttr(full_attr, value)

        return success_result(
            "Set {}.{} = {}".format(cam_node, attribute, value),
            prompt="Use get_camera_info to verify the updated camera settings.",
            camera_name=cam_node,
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

    result = set_camera_attribute("camera1", "focalLength", 50.0)
    print(json.dumps(result))
