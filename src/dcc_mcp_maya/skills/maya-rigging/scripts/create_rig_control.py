"""Create an animator-friendly rig control with optional offset groups."""

from __future__ import annotations

from typing import Any, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, summarize_node, validate_node_exists

_LOCKABLE_ATTRS = {
    "tx",
    "ty",
    "tz",
    "rx",
    "ry",
    "rz",
    "sx",
    "sy",
    "sz",
    "v",
    "translateX",
    "translateY",
    "translateZ",
    "rotateX",
    "rotateY",
    "rotateZ",
    "scaleX",
    "scaleY",
    "scaleZ",
    "visibility",
}


def _shape_points(shape: str, size: float) -> List[List[float]]:
    half = float(size) * 0.5
    if shape == "square":
        return [[-half, 0.0, -half], [half, 0.0, -half], [half, 0.0, half], [-half, 0.0, half], [-half, 0.0, -half]]
    if shape == "diamond":
        return [[0.0, 0.0, -half], [half, 0.0, 0.0], [0.0, 0.0, half], [-half, 0.0, 0.0], [0.0, 0.0, -half]]
    if shape == "cross":
        return [[-half, 0.0, 0.0], [half, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, -half], [0.0, 0.0, half]]
    if shape == "cube":
        return [
            [-half, -half, -half],
            [half, -half, -half],
            [half, -half, half],
            [-half, -half, half],
            [-half, -half, -half],
            [-half, half, -half],
            [half, half, -half],
            [half, -half, -half],
            [half, half, -half],
            [half, half, half],
            [half, -half, half],
            [half, half, half],
            [-half, half, half],
            [-half, -half, half],
            [-half, half, half],
            [-half, half, -half],
        ]
    raise ValueError("Unsupported control shape: {}".format(shape))


def _create_control_curve(cmds: Any, name: str, shape: str, size: float) -> str:
    if shape == "circle":
        result = cmds.circle(name=name, normal=(0.0, 1.0, 0.0), radius=float(size), constructionHistory=False)
        return str(result[0] if isinstance(result, (list, tuple)) else result)
    return str(cmds.curve(name=name, degree=1, point=_shape_points(shape, float(size))))


def _matrix_from(cmds: Any, node: str) -> Optional[List[float]]:
    try:
        matrix = cmds.xform(node, query=True, worldSpace=True, matrix=True)
    except Exception:  # noqa: BLE001
        return None
    return list(matrix) if matrix else None


def _match_transform(cmds: Any, node: str, target: str) -> None:
    matrix = _matrix_from(cmds, target)
    if matrix:
        cmds.xform(node, worldSpace=True, matrix=matrix)
        return
    translation = cmds.xform(target, query=True, worldSpace=True, translation=True)
    rotation = cmds.xform(target, query=True, worldSpace=True, rotation=True)
    if translation:
        cmds.xform(node, worldSpace=True, translation=translation)
    if rotation:
        cmds.xform(node, worldSpace=True, rotation=rotation)


def _make_offset_groups(cmds: Any, control: str, count: int) -> List[str]:
    count = max(0, int(count))
    groups: List[str] = []
    if count == 0:
        return groups
    matrix = _matrix_from(cmds, control)
    child = control
    for index in range(count):
        suffix = "zero" if index == 0 else "offset{}".format(index)
        group = str(cmds.group(empty=True, name="{}_{}".format(control, suffix)))
        if matrix:
            cmds.xform(group, worldSpace=True, matrix=matrix)
        cmds.parent(child, group)
        groups.append(group)
        child = group
    return groups


def _apply_color(cmds: Any, control: str, color_index: Optional[int]) -> None:
    if color_index is None:
        return
    shapes = cmds.listRelatives(control, shapes=True, fullPath=False) or []
    for shape in shapes:
        cmds.setAttr("{}.overrideEnabled".format(shape), True)
        cmds.setAttr("{}.overrideColor".format(shape), int(color_index))


def _lock_attrs(cmds: Any, control: str, attrs: Optional[List[str]]) -> None:
    for attr in attrs or []:
        if attr not in _LOCKABLE_ATTRS:
            raise ValueError("Unsupported lock attribute: {}".format(attr))
        cmds.setAttr("{}.{}".format(control, attr), lock=True, keyable=False, channelBox=False)


def create_rig_control(
    name: str,
    shape: str = "circle",
    size: float = 1.0,
    target: Optional[str] = None,
    match_target: bool = True,
    parent: Optional[str] = None,
    offset_groups: int = 1,
    color_index: Optional[int] = None,
    lock_attrs: Optional[List[str]] = None,
    constrain_target: bool = False,
    constraint_type: str = "parent",
) -> dict:
    """Create a rig control curve and optional zero/offset groups."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not str(name).strip():
            return maya_error("Invalid control name", "name must be a non-empty transform name.")
        if float(size) <= 0.0:
            return maya_error("Invalid control size", "size must be greater than zero.")
        if shape not in {"circle", "square", "diamond", "cross", "cube"}:
            return maya_error("Unsupported control shape", "shape must be circle, square, diamond, cross, or cube.")
        if target:
            err = validate_node_exists(cmds, target)
            if err:
                return err
        if parent:
            err = validate_node_exists(cmds, parent)
            if err:
                return err

        control = _create_control_curve(cmds, str(name), shape, float(size))
        if target and match_target:
            _match_transform(cmds, control, target)
        _apply_color(cmds, control, color_index)
        _lock_attrs(cmds, control, lock_attrs)

        groups = _make_offset_groups(cmds, control, offset_groups)
        top_node = groups[-1] if groups else control
        if parent:
            cmds.parent(top_node, parent)

        constraints: List[str] = []
        if constrain_target and target:
            if constraint_type == "parent":
                constraints = list(cmds.parentConstraint(control, target, maintainOffset=True) or [])
            elif constraint_type == "point":
                constraints = list(cmds.pointConstraint(control, target, maintainOffset=True) or [])
            elif constraint_type == "orient":
                constraints = list(cmds.orientConstraint(control, target, maintainOffset=True) or [])
            else:
                return maya_error("Unsupported constraint type", "constraint_type must be parent, point, or orient.")

        return maya_success(
            "Created rig control: {}".format(control),
            control=control,
            top_node=top_node,
            offset_groups=groups,
            target=target,
            constraints=constraints,
            node=summarize_node(cmds, control),
            prompt="Use create_constraint or set_driven_key to connect this control to rig behavior.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create rig control")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_rig_control`."""
    return create_rig_control(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
