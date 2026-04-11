"""Create a nurbs control curve shape for rigging."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

_SHAPES = {
    "circle": [
        (0, 0, 1),
        (0.7, 0, 0.7),
        (1, 0, 0),
        (0.7, 0, -0.7),
        (0, 0, -1),
        (-0.7, 0, -0.7),
        (-1, 0, 0),
        (-0.7, 0, 0.7),
        (0, 0, 1),
    ],
    "square": [
        (1, 0, 1),
        (1, 0, -1),
        (-1, 0, -1),
        (-1, 0, 1),
        (1, 0, 1),
    ],
    "triangle": [
        (0, 0, 1),
        (1, 0, -1),
        (-1, 0, -1),
        (0, 0, 1),
    ],
    "arrow": [
        (0, 0, -2),
        (0.5, 0, -1),
        (0.25, 0, -1),
        (0.25, 0, 1),
        (-0.25, 0, 1),
        (-0.25, 0, -1),
        (-0.5, 0, -1),
        (0, 0, -2),
    ],
    "diamond": [
        (0, 1, 0),
        (1, 0, 0),
        (0, -1, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (0, -1, 0),
        (0, 0, -1),
        (0, 1, 0),
    ],
}

def create_control_curve(
    shape: str = "circle",
    name: Optional[str] = None,
    scale: float = 1.0,
    color: Optional[int] = None,
) -> dict:
    """Create a nurbs control curve shape for rigging.

    Args:
        shape: Preset shape name: ``circle`` (default), ``square``,
            ``triangle``, ``arrow``, ``diamond``.
        name: Optional name for the created curve transform node.
        scale: Uniform scale multiplier applied to all CVs.  Default: 1.0.
        color: Maya color index (1-31) to override the curve display color.
            If None, no override is applied.

    Returns:
        ActionResultModel dict with ``context.curve_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        pts = _SHAPES.get(shape)
        if pts is None:
            return maya_error(
                "Unknown shape: {}".format(shape),
                "Valid shapes: {}".format(", ".join(sorted(_SHAPES.keys()))),
            )

        scaled = [(x * scale, y * scale, z * scale) for x, y, z in pts]
        degree = 1

        curve_kwargs = {"point": scaled, "degree": degree}  # type: dict
        if name:
            curve_kwargs["name"] = name

        crv = cmds.curve(**curve_kwargs)

        if color is not None:
            shape_node = cmds.listRelatives(crv, shapes=True)[0]
            cmds.setAttr("{}.overrideEnabled".format(shape_node), True)
            cmds.setAttr("{}.overrideColor".format(shape_node), int(color))

        return maya_success(
            "Created control curve '{}' (shape={}, scale={})".format(crv, shape, scale),
            prompt="Use lock_hide_attributes to clean up the control's channel box.",
            curve_name=crv,
            shape=shape,
            scale=scale,
            color=color,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create control curve '{}'".format(name or shape))

def main(**kwargs):
    return create_control_curve(**kwargs)

if __name__ == "__main__":
    import json

    result = create_control_curve(shape="circle", name="ctrl_root")
    print(json.dumps(result))
