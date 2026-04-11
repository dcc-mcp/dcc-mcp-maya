"""Set an attribute on a Maya camera."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, camera_name)
        if err:
            return err

        # Resolve shape node if transform was supplied
        node_type = cmds.objectType(camera_name)
        if node_type == "transform":
            shapes = cmds.listRelatives(camera_name, shapes=True, type="camera") or []
            if not shapes:
                return skill_error(
                    "No camera shape under '{}'".format(camera_name),
                    "Transform has no camera shape",
                )
            cam_node = shapes[0]
        else:
            cam_node = camera_name

        full_attr = "{}.{}".format(cam_node, attribute)
        cmds.setAttr(full_attr, value)

        return skill_success(
            "Set {}.{} = {}".format(cam_node, attribute, value),
            prompt="Use get_camera_info to verify the updated camera settings.",
            camera_name=cam_node,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set camera attribute")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_camera_attribute`."""
    return set_camera_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
