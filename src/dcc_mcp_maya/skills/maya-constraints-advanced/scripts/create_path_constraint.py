"""Attach an object to a motion path (NURBS curve)."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Attach an object to a NURBS curve using motionPath.

    Args:
        params: Dictionary containing:
            - object (str): Name of the object to constrain. Required.
            - curve (str): Name of the NURBS curve path. Required.
            - follow (bool): Enable follow (bank) rotation along path. Default True.
            - front_axis (str): Front axis: 'x', 'y', or 'z'. Default 'x'.
            - up_axis (str): Up axis: 'x', 'y', or 'z'. Default 'y'.
            - name (str): Optional name for the motionPath node.

    Returns:
        ActionResultModel with motion_path node name.
    """
    obj = params.get("object", "")
    curve = params.get("curve", "")
    follow = bool(params.get("follow", True))
    front_axis = str(params.get("front_axis", "x")).lower()
    up_axis = str(params.get("up_axis", "y")).lower()
    name = params.get("name", "")

    if not obj or not curve:
        return error_result(
            "Invalid parameters",
            "Both 'object' and 'curve' are required.",
        )

    axis_map = {"x": 0, "y": 1, "z": 2}
    if front_axis not in axis_map or up_axis not in axis_map:
        return error_result(
            "Invalid axis",
            "front_axis and up_axis must each be 'x', 'y', or 'z'.",
        )

    try:
        kwargs: Dict[str, object] = {
            "follow": follow,
            "frontAxis": axis_map[front_axis],
            "upAxis": axis_map[up_axis],
        }
        if name:
            kwargs["name"] = name

        result = cmds.pathAnimation(obj, curve, **kwargs)
        return success_result(
            "Attached '{}' to path '{}'".format(obj, curve),
            prompt="Animate the motionPath.uValue attribute to move along the path.",
            motion_path=result,
            object=obj,
            curve=curve,
        )
    except Exception as exc:
        return error_result("Failed to create path constraint", str(exc))
