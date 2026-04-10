"""Enable or configure stretch/squash on a Spline IK handle."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Set stretch and squash attributes on a Spline IK handle.

    Args:
        params: Dictionary containing:
            - ik_handle (str): Name of the spline IK handle. Required.
            - stretch (bool): Enable stretch (dStretch). Default True.
            - squash (bool): Enable squash (dSquash). Default False.

    Returns:
        ActionResultModel confirming the stretch settings were applied.
    """
    ik_handle = params.get("ik_handle", "")
    stretch = bool(params.get("stretch", True))
    squash = bool(params.get("squash", False))

    if not ik_handle:
        return error_result("Invalid parameters", "Parameter 'ik_handle' is required.")

    try:
        if not cmds.objExists(ik_handle):
            return error_result(
                "IK handle not found",
                "No node named '{}' in the scene.".format(ik_handle),
            )
        cmds.setAttr("{}.dStretch".format(ik_handle), int(stretch))
        cmds.setAttr("{}.dSquash".format(ik_handle), int(squash))
        return success_result(
            "Set stretch={}, squash={} on '{}'".format(stretch, squash, ik_handle),
            prompt="Animate the curve CVs to drive the joint chain along the spline.",
            ik_handle=ik_handle,
            stretch=stretch,
            squash=squash,
        )
    except Exception as exc:
        return error_result("Failed to set spline IK stretch", str(exc))
