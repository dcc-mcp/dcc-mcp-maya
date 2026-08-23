"""Create a single Maya light and return both transform and shape names."""

from __future__ import annotations

import math
from typing import Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SUPPORTED_LIGHT_TYPES = {
    "ambientLight",
    "areaLight",
    "directionalLight",
    "pointLight",
    "spotLight",
    "volumeLight",
    "aiSkyDomeLight",
}


def _validated_float3(field: str, value, fallback):
    if value is None:
        return [float(item) for item in fallback]
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("{} must contain exactly three numbers".format(field))
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ValueError("{} must contain only numbers".format(field))
    values = [float(item) for item in value]
    if not all(math.isfinite(item) for item in values):
        raise ValueError("{} values must be finite".format(field))
    return values


def _safe_set_attr(cmds, plug: str, value) -> bool:
    try:
        cmds.setAttr(plug, value)
        return True
    except Exception:
        return False


def create_light(
    name: str = "mcpLight",
    light_type: str = "directionalLight",
    intensity: float = 1.0,
    color: Optional[list] = None,
    position: Optional[list] = None,
    rotation: Optional[list] = None,
    parent: Optional[str] = None,
    cone_angle: Optional[float] = None,
    penumbra_angle: Optional[float] = None,
) -> dict:
    """Create one light with a transform parent.

    This avoids the Maya 2022 ``cmds.directionalLight()`` trap where the
    command returns the shape node, not the transform.  The returned envelope
    always includes both names so agents can move the transform safely.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if light_type not in _SUPPORTED_LIGHT_TYPES:
            return skill_error(
                "Unsupported light_type",
                "light_type must be one of: {}".format(", ".join(sorted(_SUPPORTED_LIGHT_TYPES))),
                light_type=light_type,
            )
        if parent and not cmds.objExists(parent):
            return skill_error("Parent node not found", "The supplied parent transform does not exist.", parent=parent)

        try:
            rgb = _validated_float3("color", color, [1.0, 1.0, 1.0])
            position_values = _validated_float3("position", position, [0.0, 0.0, 0.0])
            rotation_values = _validated_float3("rotation", rotation, [0.0, 0.0, 0.0])
        except ValueError as exc:
            field = str(exc).split(" ", 1)[0]
            return skill_error(
                "Invalid light vector",
                "INVALID_LIGHT_VECTOR",
                field=field,
                detail=str(exc),
            )

        transform = (
            cmds.createNode("transform", name=name, parent=parent)
            if parent
            else cmds.createNode("transform", name=name)
        )
        cmds.shadingNode(light_type, asLight=True, name="{}Shape".format(transform), parent=transform)
        shape = cmds.listRelatives(transform, shapes=True, type=light_type, fullPath=False)[0]

        cmds.setAttr("{}.translate".format(transform), *position_values, type="double3")
        cmds.setAttr("{}.rotate".format(transform), *rotation_values, type="double3")
        _safe_set_attr(cmds, "{}.intensity".format(shape), float(intensity))
        try:
            cmds.setAttr("{}.color".format(shape), *rgb, type="double3")
        except Exception:
            for channel, channel_value in zip(("R", "G", "B"), rgb):
                _safe_set_attr(cmds, "{}.color{}".format(shape, channel), channel_value)

        if light_type == "spotLight":
            if cone_angle is not None:
                _safe_set_attr(cmds, "{}.coneAngle".format(shape), float(cone_angle))
            if penumbra_angle is not None:
                _safe_set_attr(cmds, "{}.penumbraAngle".format(shape), float(penumbra_angle))

        return skill_success(
            "Created {} light '{}'".format(light_type, transform),
            transform=transform,
            shape=shape,
            light_type=light_type,
            intensity=float(intensity),
            color=rgb,
            position=position_values,
            rotation=rotation_values,
            parent=parent,
            prompt="Move or rotate context.transform; light command return values can be shape nodes in Maya 2022.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create light '{}'".format(name))


@skill_entry
def main(**kwargs) -> dict:
    return create_light(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
