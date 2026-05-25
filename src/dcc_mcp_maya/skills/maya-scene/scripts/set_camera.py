"""Edit common Maya camera transform and shape attributes."""

from __future__ import annotations

from typing import Any, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, summarize_node, validate_node_exists


def _as_vector(value: Optional[List[float]], name: str) -> Optional[List[float]]:
    if value is None:
        return None
    if len(value) != 3:
        raise ValueError("{} must contain exactly three numbers".format(name))
    return [float(value[0]), float(value[1]), float(value[2])]


def _camera_shape(cmds: Any, camera: str) -> str:
    try:
        if cmds.nodeType(camera) == "camera":
            return camera
    except Exception:  # noqa: BLE001
        pass
    shapes = cmds.listRelatives(camera, shapes=True, fullPath=False) or []
    for shape in shapes:
        try:
            if cmds.nodeType(shape) == "camera":
                return str(shape)
        except Exception:  # noqa: BLE001
            continue
    raise ValueError("{} is not a camera transform or shape".format(camera))


def _camera_transform(cmds: Any, camera_or_shape: str) -> str:
    try:
        if cmds.nodeType(camera_or_shape) != "camera":
            return camera_or_shape
    except Exception:  # noqa: BLE001
        return camera_or_shape
    parents = cmds.listRelatives(camera_or_shape, parent=True, fullPath=False) or []
    return str(parents[0]) if parents else camera_or_shape


def _set_attr_if_value(cmds: Any, plug: str, value: Any, updates: dict, key: str) -> None:
    if value is None:
        return
    cmds.setAttr(plug, value)
    updates[key] = value


def _aim_camera_at_point(cmds: Any, camera: str, point: List[float]) -> bool:
    locator = None
    constraint = None
    try:
        locator = (cmds.spaceLocator(name="{}_look_at_tmp".format(camera)) or [None])[0]
        if not locator:
            return False
        cmds.xform(locator, worldSpace=True, translation=point)
        constraint = (
            cmds.aimConstraint(
                locator,
                camera,
                aimVector=(0.0, 0.0, -1.0),
                upVector=(0.0, 1.0, 0.0),
                worldUpType="scene",
            )
            or [None]
        )[0]
        if constraint:
            cmds.delete(constraint)
        cmds.delete(locator)
        return True
    except Exception:  # noqa: BLE001
        for node in (constraint, locator):
            if node:
                try:
                    cmds.delete(node)
                except Exception:  # noqa: BLE001
                    pass
        return False


def set_camera(
    camera: str,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    look_at: Optional[List[float]] = None,
    focal_length: Optional[float] = None,
    near_clip: Optional[float] = None,
    far_clip: Optional[float] = None,
    renderable: Optional[bool] = None,
    orthographic: Optional[bool] = None,
    orthographic_width: Optional[float] = None,
) -> dict:
    """Edit a camera transform and common shape attributes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, camera)
        if err:
            return err
        shape = _camera_shape(cmds, camera)
        transform = _camera_transform(cmds, camera)

        updates = {}
        translate = _as_vector(position, "position")
        rotate = _as_vector(rotation, "rotation")
        if translate is not None:
            cmds.xform(transform, worldSpace=True, translation=translate)
            updates["position"] = translate
        if rotate is not None:
            cmds.xform(transform, worldSpace=True, rotation=rotate)
            updates["rotation"] = rotate
        if look_at is not None:
            look_at_point = _as_vector(look_at, "look_at")
            updates["look_at"] = look_at_point
            updates["look_at_applied"] = _aim_camera_at_point(cmds, transform, look_at_point or [0.0, 0.0, 0.0])

        _set_attr_if_value(cmds, "{}.focalLength".format(shape), focal_length, updates, "focal_length")
        _set_attr_if_value(cmds, "{}.nearClipPlane".format(shape), near_clip, updates, "near_clip")
        _set_attr_if_value(cmds, "{}.farClipPlane".format(shape), far_clip, updates, "far_clip")
        _set_attr_if_value(cmds, "{}.renderable".format(shape), renderable, updates, "renderable")
        _set_attr_if_value(cmds, "{}.orthographic".format(shape), orthographic, updates, "orthographic")
        _set_attr_if_value(
            cmds,
            "{}.orthographicWidth".format(shape),
            orthographic_width,
            updates,
            "orthographic_width",
        )

        if not updates:
            return maya_error("No camera changes requested", "Pass at least one transform or camera attribute.")

        return maya_success(
            "Updated camera: {}".format(transform),
            camera=transform,
            camera_shape=shape,
            updates=updates,
            node=summarize_node(cmds, transform),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to update camera")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_camera`."""
    return set_camera(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
