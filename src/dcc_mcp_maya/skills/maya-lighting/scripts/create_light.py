"""Create a Maya light of the specified type."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Supported Maya light types and their corresponding command/node names
_LIGHT_TYPE_MAP = {
    "point": "pointLight",
    "spot": "spotLight",
    "directional": "directionalLight",
    "area": "areaLight",
    "ambient": "ambientLight",
}


def create_light(
    light_type: str = "point",
    name: Optional[str] = None,
    intensity: float = 1.0,
    color: Optional[List[float]] = None,
    position: Optional[List[float]] = None,
) -> dict:
    """Create a Maya light of the specified type.

    Args:
        light_type: One of ``"point"``, ``"spot"``, ``"directional"``,
            ``"area"``, ``"ambient"``.  Default: ``"point"``.
        name: Optional name for the light transform node.
        intensity: Initial light intensity.  Default: 1.0.
        color: RGB colour as ``[r, g, b]`` in 0-1 range.  Default: white.
        position: World-space position ``[x, y, z]``.  Default: [0, 0, 0].

    Returns:
        ActionResultModel dict with ``context.light_name`` and
        ``context.light_shape``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    lt = light_type.lower()
    if lt not in _LIGHT_TYPE_MAP:
        return error_result(
            "Unsupported light type: {}".format(light_type),
            "Supported types: {}".format(", ".join(sorted(_LIGHT_TYPE_MAP))),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        create_cmd = getattr(cmds, _LIGHT_TYPE_MAP[lt])
        kwargs = {}
        if name:
            kwargs["name"] = name
        shape = create_cmd(**kwargs)
        # For directional/area/ambient cmds return shape; for point/spot they
        # return a list [shape, transform] or just the shape depending on version.
        if isinstance(shape, (list, tuple)):
            shape = shape[0]

        # Find the transform parent of the shape
        transform = cmds.listRelatives(shape, parent=True)
        transform = transform[0] if transform else shape

        # Apply intensity
        cmds.setAttr("{}.intensity".format(shape), intensity)

        # Apply colour
        r, g, b = (color[0], color[1], color[2]) if color and len(color) >= 3 else (1.0, 1.0, 1.0)
        cmds.setAttr("{}.color".format(shape), r, g, b, type="double3")

        # Apply position
        if position and len(position) >= 3:
            cmds.setAttr("{}.translate".format(transform), position[0], position[1], position[2], type="double3")

        return success_result(
            "Created {} light '{}'".format(lt, transform),
            light_name=transform,
            light_shape=shape,
            light_type=lt,
            intensity=intensity,
            color=[r, g, b],
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_light failed")
        return error_result("Failed to create light", str(exc)).to_dict()



def main(**kwargs):
    return create_light(**kwargs)


if __name__ == "__main__":
    import json
    result = create_light()
    print(json.dumps(result))
