"""Create a rig control curve with a standard shape."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)

_SHAPES = {
    "circle": lambda name: cmds.circle(name=name, normal=(0, 1, 0), radius=1.0, constructionHistory=False)[0],
    "square": lambda name: cmds.curve(
        name=name, degree=1,
        point=[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (-1, 0, -1)],
    ),
    "cross": lambda name: cmds.curve(
        name=name, degree=1,
        point=[
            (-0.33, 0, -1), (0.33, 0, -1), (0.33, 0, -0.33),
            (1, 0, -0.33), (1, 0, 0.33), (0.33, 0, 0.33),
            (0.33, 0, 1), (-0.33, 0, 1), (-0.33, 0, 0.33),
            (-1, 0, 0.33), (-1, 0, -0.33), (-0.33, 0, -0.33),
            (-0.33, 0, -1),
        ],
    ),
    "locator": lambda name: cmds.spaceLocator(name=name)[0],
}


def run(params: Dict[str, object]) -> object:
    """Create a rig control curve at the world origin.

    Args:
        params: Dictionary containing:
            - name (str): Name for the control.  Default 'ctrl'.
            - shape (str): 'circle', 'square', 'cross', or 'locator'.
                           Default 'circle'.
            - color (int): Maya override colour index (1-31).  Default 17 (yellow).
            - scale (float): Uniform scale factor.  Default 1.0.

    Returns:
        ActionResultModel with control transform name.
    """
    name = str(params.get("name", "ctrl")).strip() or "ctrl"
    shape = str(params.get("shape", "circle")).lower()
    try:
        color = int(params.get("color", 17))
    except (TypeError, ValueError):
        color = 17
    try:
        scale = float(params.get("scale", 1.0))
    except (TypeError, ValueError):
        scale = 1.0

    if shape not in _SHAPES:
        return error_result(
            "Invalid shape",
            "shape must be one of: {}.".format(", ".join(sorted(_SHAPES))),
        )

    try:
        ctrl = _SHAPES[shape](name)
        if scale != 1.0:
            cmds.scale(scale, scale, scale, ctrl)
            cmds.makeIdentity(ctrl, apply=True, scale=True)

        # Apply colour override
        shapes = cmds.listRelatives(ctrl, shapes=True) or [ctrl]
        for s in shapes:
            cmds.setAttr("{}.overrideEnabled".format(s), True)
            cmds.setAttr("{}.overrideColor".format(s), color)

        return success_result(
            "Created control curve '{}' with shape '{}'".format(ctrl, shape),
            prompt="Use add_offset_group to add an offset group above the control.",
            control=ctrl,
            shape=shape,
            color=color,
        )
    except Exception as exc:
        logger.exception("create_control_curve failed")
        return error_result("Failed to create control curve '{}'".format(name), str(exc))
