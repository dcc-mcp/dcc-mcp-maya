"""Maya camera management actions."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional

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
        ActionResultModel dict with ``context.camera_name`` (transform) and
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

        return maya_success(
            "Created camera '{}'".format(transform),
            camera_name=transform,
            camera_shape=shape,
            focal_length=focal_length,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to create camera")

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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return maya_error("Camera not found: {}".format(camera_name))

        shapes = cmds.listRelatives(camera_name, shapes=True) or []
        shape = shapes[0] if shapes else camera_name

        full_attr = "{}.{}".format(shape, attribute)
        if not cmds.objExists(full_attr):
            full_attr = "{}.{}".format(camera_name, attribute)
        if not cmds.objExists(full_attr):
            return maya_error("Attribute '{}' not found on camera '{}'".format(attribute, camera_name))

        if isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        elif isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(full_attr, value[0], value[1], value[2], type="double3")
        else:
            cmds.setAttr(full_attr, value)

        return maya_success(
            "Set {}.{} = {}".format(camera_name, attribute, value),
            camera_name=camera_name,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to set camera attribute")

def get_camera_info(camera_name: str) -> dict:
    """Query detailed information about a camera.

    Args:
        camera_name: Transform or shape name of the camera.

    Returns:
        ActionResultModel dict with ``context`` containing focal_length,
        near/far clip, position, rotation, renderable, and field of view.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(camera_name):
            return maya_error("Camera not found: {}".format(camera_name))

        shapes = cmds.listRelatives(camera_name, shapes=True) or []
        if not shapes:
            # camera_name might already be a shape
            if cmds.objectType(camera_name) == "camera":
                shape = camera_name
                transform_list = cmds.listRelatives(camera_name, parent=True) or [camera_name]
                transform = transform_list[0]
            else:
                return maya_error("'{}' is not a camera".format(camera_name))
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

        return maya_success("Camera info for '{}'".format(transform), **info)
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to get camera info")

def list_all_cameras(include_default: bool = True) -> dict:
    """List all cameras in the scene with basic attributes.

    Args:
        include_default: If False, omit Maya's default cameras
            (``persp``, ``top``, ``front``, ``side``).  Default: True.

    Returns:
        ActionResultModel dict with ``context.cameras`` list.
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

        return maya_success(
            "Found {} camera(s)".format(len(results)),
            cameras=results,
            count=len(results),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to list cameras")
