"""Maya camera management actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_camera(
    name: Optional[str] = None,
    focal_length: float = 35.0,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
) -> dict:
    """Create a new Maya camera.

    Args:
        name: Optional transform name for the new camera.
        focal_length: Camera focal length in mm.  Default: 35.0.
        position: World-space position ``[x, y, z]``.  Default: origin.
        rotation: Euler rotation ``[rx, ry, rz]`` in degrees.  Default: none.

    Returns:
        ToolResult dict with ``context.camera_name`` (transform) and
        ``context.camera_shape``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.camera()
        transform = result[0]
        shape = result[1]

        if name:
            transform = cmds.rename(transform, name)
            # Shape is renamed automatically
            shapes = cmds.listRelatives(transform, shapes=True) or []
            shape = shapes[0] if shapes else shape

        cmds.setAttr("{}.focalLength".format(shape), focal_length)

        if position and len(position) >= 3:
            cmds.setAttr(
                "{}.translate".format(transform),
                position[0],
                position[1],
                position[2],
                type="double3",
            )
        if rotation and len(rotation) >= 3:
            cmds.setAttr(
                "{}.rotate".format(transform),
                rotation[0],
                rotation[1],
                rotation[2],
                type="double3",
            )

        return skill_success(
            "Created camera '{}'".format(transform),
            camera_name=transform,
            camera_shape=shape,
            focal_length=focal_length,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create camera")


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
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, camera_name)
        if err:
            return err

        shapes = cmds.listRelatives(camera_name, shapes=True) or []
        shape = shapes[0] if shapes else camera_name

        full_attr = "{}.{}".format(shape, attribute)
        if not cmds.objExists(full_attr):
            full_attr = "{}.{}".format(camera_name, attribute)
        err = validate_node_exists(cmds, full_attr)
        if err:
            return err

        if isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        elif isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(full_attr, value[0], value[1], value[2], type="double3")
        else:
            cmds.setAttr(full_attr, value)

        return skill_success(
            "Set {}.{} = {}".format(camera_name, attribute, value),
            camera_name=camera_name,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set camera attribute")


def get_camera_info(camera_name: str) -> dict:
    """Query detailed information about a camera.

    Args:
        camera_name: Transform or shape name of the camera.

    Returns:
        ToolResult dict with ``context`` containing focal_length,
        near/far clip, position, rotation, renderable, and field of view.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, camera_name)
        if err:
            return err

        shapes = cmds.listRelatives(camera_name, shapes=True) or []
        if not shapes:
            # camera_name might already be a shape
            if cmds.objectType(camera_name) == "camera":
                shape = camera_name
                transform_list = cmds.listRelatives(camera_name, parent=True) or [camera_name]
                transform = transform_list[0]
            else:
                return skill_error("'{}' is not a camera".format(camera_name))
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

        return skill_success(
            "Camera info for '{}'".format(transform),
            **info,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get camera info")


def list_all_cameras(include_default: bool = True) -> dict:
    """List all cameras in the scene with basic attributes.

    Args:
        include_default: If False, omit Maya's default cameras
            (``persp``, ``top``, ``front``, ``side``).  Default: True.

    Returns:
        ToolResult dict with ``context.cameras`` list.
    """

    _DEFAULT_CAMERAS = {"persp", "top", "front", "side"}

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        shapes = cmds.ls(type="camera") or []
        results = []
        for shape in shapes:
            transform_list = cmds.listRelatives(shape, parent=True) or [shape]
            transform = transform_list[0]
            if not include_default and transform in _DEFAULT_CAMERAS:
                continue
            entry = {"name": transform, "shape": shape}
            for attr in ("focalLength", "renderable"):
                try:
                    entry[attr] = cmds.getAttr("{}.{}".format(shape, attr))
                except Exception:
                    entry[attr] = None
            results.append(entry)

        return skill_success(
            "Found {} camera(s)".format(len(results)),
            cameras=results,
            count=len(results),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list cameras")
