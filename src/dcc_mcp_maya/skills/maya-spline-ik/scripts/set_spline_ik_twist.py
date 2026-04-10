"""Set twist attributes on a Spline IK handle."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Set world-up type and twist controls on a Spline IK handle.

    Args:
        params: Dictionary containing:
            - ik_handle (str): Name of the spline IK handle. Required.
            - world_up_type (int): World-up type index (0=scene, 1=object, 2=objectRotation,
              3=objectRotationUp, 4=vector, 5=objectRotationPlane). Default 0.
            - twist (float): Twist offset in degrees applied to the chain. Default 0.0.

    Returns:
        ActionResultModel confirming the twist settings were applied.
    """
    ik_handle = params.get("ik_handle", "")
    world_up_type = int(params.get("world_up_type", 0))
    twist = float(params.get("twist", 0.0))

    if not ik_handle:
        return error_result("Invalid parameters", "Parameter 'ik_handle' is required.")

    try:
        if not cmds.objExists(ik_handle):
            return error_result(
                "IK handle not found",
                "No node named '{}' in the scene.".format(ik_handle),
            )
        cmds.setAttr("{}.dWorldUpType".format(ik_handle), world_up_type)
        cmds.setAttr("{}.twist".format(ik_handle), twist)
        return success_result(
            "Set worldUpType={}, twist={} on '{}'".format(world_up_type, twist, ik_handle),
            prompt="Use set_spline_ik_stretch to also control squash/stretch behavior.",
            ik_handle=ik_handle,
            world_up_type=world_up_type,
            twist=twist,
        )
    except Exception as exc:
        return error_result("Failed to set spline IK twist", str(exc))
