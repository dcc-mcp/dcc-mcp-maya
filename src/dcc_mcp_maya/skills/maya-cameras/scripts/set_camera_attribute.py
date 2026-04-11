"""Set an attribute on a Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return maya_error(
                "Camera not found: {}".format(camera_name),
                "'{}' does not exist".format(camera_name),
            )

        # Resolve shape node if transform was supplied
        node_type = cmds.objectType(camera_name)
        if node_type == "transform":
            shapes = cmds.listRelatives(camera_name, shapes=True, type="camera") or []
            if not shapes:
                return maya_error(
                    "No camera shape under '{}'".format(camera_name),
                    "Transform has no camera shape",
                )
            cam_node = shapes[0]
        else:
            cam_node = camera_name

        full_attr = "{}.{}".format(cam_node, attribute)
        cmds.setAttr(full_attr, value)

        return maya_success(
            "Set {}.{} = {}".format(cam_node, attribute, value),
            prompt="Use get_camera_info to verify the updated camera settings.",
            camera_name=cam_node,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set camera attribute")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_camera_attribute`."""
    return set_camera_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_camera_attribute("camera1", "focalLength", 50.0)
    print(json.dumps(result))
