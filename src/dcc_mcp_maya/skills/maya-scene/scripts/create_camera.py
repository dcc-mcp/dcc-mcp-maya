"""Create a Maya camera."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, summarize_node


def _as_vector(value: Optional[List[float]], default: List[float], name: str) -> List[float]:
    vector = default if value is None else value
    if len(vector) != 3:
        raise ValueError("{} must contain exactly three numbers".format(name))
    return [float(vector[0]), float(vector[1]), float(vector[2])]


def _set_attr_if_exists(cmds: Any, plug: str, value: Any) -> None:
    try:
        exists = getattr(cmds, "objExists", None)
        if callable(exists) and not exists(plug):
            return
    except Exception:  # noqa: BLE001
        pass
    cmds.setAttr(plug, value)


def _camera_result(cmds: Any, result: Any, requested_name: Optional[str]) -> Dict[str, str]:
    if not isinstance(result, (list, tuple)) or len(result) < 2:
        raise ValueError("cmds.camera returned an unexpected result: {!r}".format(result))
    transform = str(result[0])
    shape = str(result[1])
    if requested_name and transform != requested_name:
        transform = str(cmds.rename(transform, requested_name))
        shapes = cmds.listRelatives(transform, shapes=True, fullPath=False) or [shape]
        shape = str(shapes[0])
    return {"camera": transform, "camera_shape": shape}


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


def create_camera(
    name: Optional[str] = None,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    look_at: Optional[List[float]] = None,
    focal_length: float = 35.0,
    near_clip: float = 0.1,
    far_clip: float = 10000.0,
    renderable: bool = True,
    orthographic: bool = False,
    orthographic_width: Optional[float] = None,
) -> dict:
    """Create a camera transform and shape with common camera attributes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.camera()
        camera_info = _camera_result(cmds, result, name)
        camera = camera_info["camera"]
        shape = camera_info["camera_shape"]

        translate = _as_vector(position, [0.0, 2.0, 10.0], "position")
        cmds.xform(camera, worldSpace=True, translation=translate)
        if rotation is not None:
            cmds.xform(camera, worldSpace=True, rotation=_as_vector(rotation, [0.0, 0.0, 0.0], "rotation"))

        look_at_applied = False
        if look_at is not None:
            look_at_applied = _aim_camera_at_point(cmds, camera, _as_vector(look_at, [0.0, 0.0, 0.0], "look_at"))

        _set_attr_if_exists(cmds, "{}.focalLength".format(shape), float(focal_length))
        _set_attr_if_exists(cmds, "{}.nearClipPlane".format(shape), float(near_clip))
        _set_attr_if_exists(cmds, "{}.farClipPlane".format(shape), float(far_clip))
        _set_attr_if_exists(cmds, "{}.renderable".format(shape), bool(renderable))
        _set_attr_if_exists(cmds, "{}.orthographic".format(shape), bool(orthographic))
        if orthographic_width is not None:
            _set_attr_if_exists(cmds, "{}.orthographicWidth".format(shape), float(orthographic_width))

        return maya_success(
            "Created camera: {}".format(camera),
            camera=camera,
            camera_shape=shape,
            node=summarize_node(cmds, camera),
            settings={
                "position": translate,
                "rotation": rotation,
                "look_at": look_at,
                "look_at_applied": look_at_applied,
                "focal_length": float(focal_length),
                "near_clip": float(near_clip),
                "far_clip": float(far_clip),
                "renderable": bool(renderable),
                "orthographic": bool(orthographic),
                "orthographic_width": orthographic_width,
            },
            prompt="Use look_through_camera or maya-render capture_playblast_sequence to preview this camera.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create camera")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_camera`."""
    return create_camera(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
