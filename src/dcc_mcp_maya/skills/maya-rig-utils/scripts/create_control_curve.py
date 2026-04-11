"""Create a nurbs control curve shape for rigging."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        pts = _SHAPES.get(shape)
        if pts is None:
            return error_result(
                "Unknown shape: {}".format(shape),
                "Valid shapes: {}".format(", ".join(sorted(_SHAPES.keys()))),
            ).to_dict()

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

        return success_result(
            "Created control curve '{}' (shape={}, scale={})".format(crv, shape, scale),
            prompt="Use lock_hide_attributes to clean up the control's channel box.",
            curve_name=crv,
            shape=shape,
            scale=scale,
            color=color,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_control_curve failed")
        return error_result("Failed to create control curve '{}'".format(name or shape), str(exc)).to_dict()


def main(**kwargs):
    return create_control_curve(**kwargs)


if __name__ == "__main__":
    import json

    result = create_control_curve(shape="circle", name="ctrl_root")
    print(json.dumps(result))
