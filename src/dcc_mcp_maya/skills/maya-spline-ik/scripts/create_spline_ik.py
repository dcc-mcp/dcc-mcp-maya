"""Create a Spline IK handle on a joint chain."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Create a Spline IK handle driven by a curve.

    Args:
        params: Dictionary containing:
            - start_joint (str): Name of the start joint. Required.
            - end_joint (str): Name of the end/effector joint. Required.
            - curve (str): Name of an existing NURBS curve. If omitted, Maya auto-creates one.
            - name (str): Optional name prefix for the IK handle/effector.

    Returns:
        ActionResultModel with ik_handle, effector, and curve names.
    """
    start_joint = params.get("start_joint", "")
    end_joint = params.get("end_joint", "")
    curve = params.get("curve", "")
    name = params.get("name", "")

    if not start_joint or not end_joint:
        return error_result(
            "Invalid parameters",
            "Both 'start_joint' and 'end_joint' are required.",
        )

    try:
        kwargs: Dict[str, object] = {"solver": "ikSplineSolver"}
        if curve:
            kwargs["curve"] = curve
            kwargs["createCurve"] = False
        else:
            kwargs["createCurve"] = True
        if name:
            kwargs["name"] = "{}_ikHandle".format(name)

        result = cmds.ikHandle(start_joint, end_joint, **kwargs)
        ik_handle = result[0]
        effector = result[1]
        used_curve = result[2] if len(result) > 2 else curve

        return success_result(
            "Created spline IK handle '{}'".format(ik_handle),
            prompt="Use set_spline_ik_stretch to enable stretch/squash on the IK chain.",
            ik_handle=ik_handle,
            effector=effector,
            curve=used_curve,
        )
    except Exception as exc:
        return error_result("Failed to create spline IK handle", str(exc))
