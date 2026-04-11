"""Create a Maya light."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_LIGHT_TYPES = {
    "directional": "directionalLight",
    "point": "pointLight",
    "spot": "spotLight",
    "area": "areaLight",
    "ambient": "ambientLight",
}


def create_light(
    light_type: str = "point",
    name: Optional[str] = None,
    intensity: float = 1.0,
    color: Optional[List[float]] = None,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
) -> dict:
    """Create a Maya light of the specified type.

    Args:
        light_type: One of ``directional``, ``point``, ``spot``, ``area``,
            ``ambient``.
        name: Optional name for the light transform node.
        intensity: Light intensity.  Default 1.0.
        color: Optional RGB color as ``[r, g, b]`` in 0–1 range.
        position: Optional ``[x, y, z]`` world-space position.
        rotation: Optional ``[rx, ry, rz]`` rotation in degrees.

    Returns:
        ActionResultModel dict with ``context.transform`` and ``context.shape``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if light_type not in _LIGHT_TYPES:
            return error_result(
                "Unknown light type: {}".format(light_type),
                "Supported types: {}".format(", ".join(sorted(_LIGHT_TYPES))),
            ).to_dict()

        cmd_fn = getattr(cmds, _LIGHT_TYPES[light_type])
        shape = cmd_fn(intensity=intensity)
        shapes = cmds.listRelatives(shape, parent=True) or [shape]
        transform = shapes[0]

        if name:
            transform = cmds.rename(transform, name)
            all_shapes = cmds.listRelatives(transform, shapes=True, fullPath=False) or []
            shape = all_shapes[0] if all_shapes else shape

        if color and len(color) == 3:
            cmds.setAttr("{}.colorR".format(shape), color[0])
            cmds.setAttr("{}.colorG".format(shape), color[1])
            cmds.setAttr("{}.colorB".format(shape), color[2])

        if position and len(position) == 3:
            cmds.move(position[0], position[1], position[2], transform)
        if rotation and len(rotation) == 3:
            cmds.rotate(rotation[0], rotation[1], rotation[2], transform)

        return success_result(
            "Created {} light '{}'".format(light_type, transform),
            prompt="Use set_light_attribute to adjust intensity, color, or shadows.",
            transform=transform,
            shape=shape,
            light_type=light_type,
            intensity=intensity,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_light failed")
        return error_result("Failed to create light", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_light`."""
    return create_light(**kwargs)


if __name__ == "__main__":
    import json

    result = create_light("point", "myLight", intensity=2.0, color=[1.0, 0.9, 0.8])
    print(json.dumps(result))
