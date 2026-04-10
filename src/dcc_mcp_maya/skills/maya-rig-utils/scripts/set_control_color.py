"""Set the override colour on rig control curve shapes."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Apply a Maya colour index override to all curve shapes under a control.

    Args:
        params: Dictionary containing:
            - control (str): Name of the control transform.  Required.
            - color (int): Maya override colour index (1-31).  Required.

    Returns:
        ActionResultModel with control and colour index.
    """
    control = str(params.get("control", "")).strip()
    try:
        color = int(params.get("color", 0))
    except (TypeError, ValueError):
        return error_result("Invalid parameters", "'color' must be an integer.")

    if not control:
        return error_result("Invalid parameters", "'control' is required.")
    if not (1 <= color <= 31):
        return error_result(
            "Invalid colour index",
            "color must be between 1 and 31, got {}.".format(color),
        )

    try:
        if not cmds.objExists(control):
            return error_result("Control not found", "No node named '{}'.".format(control))

        shapes = cmds.listRelatives(control, shapes=True, type="nurbsCurve") or []
        if not shapes:
            shapes = cmds.listRelatives(control, shapes=True) or []
        if not shapes:
            return error_result(
                "No shapes found",
                "Control '{}' has no shape nodes.".format(control),
            )

        for shape in shapes:
            cmds.setAttr("{}.overrideEnabled".format(shape), True)
            cmds.setAttr("{}.overrideColor".format(shape), color)

        return success_result(
            "Set colour {} on control '{}'".format(color, control),
            prompt="Use create_control_curve to create new controls with preset colours.",
            control=control,
            color=color,
            shapes_modified=shapes,
        )
    except Exception as exc:
        logger.exception("set_control_color failed")
        return error_result(
            "Failed to set colour on control '{}'".format(control), str(exc)
        )
