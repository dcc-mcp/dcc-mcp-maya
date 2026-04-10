"""Mirror a rig control curve shape across a specified axis."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Duplicate and mirror a control curve shape to create the opposite-side control.

    Args:
        params: Dictionary containing:
            - control (str): Name of the source control transform.  Required.
            - target (str): Name of the destination control.  If not given,
                            the name is derived by swapping 'L_'/'R_' or '_L'/'_R'.
            - axis (str): Mirror axis: 'x', 'y', or 'z'.  Default 'x'.
            - copy_color (bool): Copy the colour override to the mirrored shapes.
                                 Default True.

    Returns:
        ActionResultModel with source and mirrored control names.
    """
    control = str(params.get("control", "")).strip()
    target = str(params.get("target", "")).strip()
    axis = str(params.get("axis", "x")).lower()
    copy_color = bool(params.get("copy_color", True))

    if not control:
        return error_result("Invalid parameters", "'control' is required.")
    if axis not in ("x", "y", "z"):
        return error_result(
            "Invalid axis",
            "axis must be 'x', 'y', or 'z', got '{}'.".format(axis),
        )

    try:
        if not cmds.objExists(control):
            return error_result("Control not found", "No node named '{}'.".format(control))

        # Derive target name if not supplied
        if not target:
            if control.startswith("L_"):
                target = "R_" + control[2:]
            elif control.startswith("R_"):
                target = "L_" + control[2:]
            elif "_L_" in control:
                target = control.replace("_L_", "_R_", 1)
            elif "_R_" in control:
                target = control.replace("_R_", "_L_", 1)
            else:
                target = control + "_mirrored"

        # Duplicate the control curve
        dup = cmds.duplicate(control, name=target, returnRootsOnly=True)[0]

        # Scale to mirror
        scale_args = {
            "x": (-1, 1, 1),
            "y": (1, -1, 1),
            "z": (1, 1, -1),
        }[axis]
        cmds.scale(*scale_args, dup, absolute=False)
        cmds.makeIdentity(dup, apply=True, scale=True)

        # Optionally copy colour
        if copy_color:
            src_shapes = cmds.listRelatives(control, shapes=True) or []
            dst_shapes = cmds.listRelatives(dup, shapes=True) or []
            for src_s, dst_s in zip(src_shapes, dst_shapes):
                if cmds.getAttr("{}.overrideEnabled".format(src_s)):
                    color_idx = cmds.getAttr("{}.overrideColor".format(src_s))
                    cmds.setAttr("{}.overrideEnabled".format(dst_s), True)
                    cmds.setAttr("{}.overrideColor".format(dst_s), color_idx)

        return success_result(
            "Mirrored control '{}' → '{}' across {} axis".format(control, dup, axis),
            prompt="Position the mirrored control and parent it into the rig hierarchy.",
            source=control,
            mirrored=dup,
            axis=axis,
        )
    except Exception as exc:
        logger.exception("mirror_control_curve failed")
        return error_result(
            "Failed to mirror control '{}'".format(control), str(exc)
        )
