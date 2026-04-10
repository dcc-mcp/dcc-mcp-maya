"""Create a tangent constraint so an object's axis aligns with a curve tangent."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Constrain an object's orientation to follow a curve tangent.

    Args:
        params: Dictionary containing:
            - target (str): The NURBS curve target. Required.
            - object (str): The object to constrain. Required.
            - aim_vector (list[float]): Axis to align with tangent, e.g. [1,0,0]. Default [1,0,0].
            - up_vector (list[float]): Up vector for orientation, e.g. [0,1,0]. Default [0,1,0].
            - weight (float): Constraint weight 0-1. Default 1.0.
            - name (str): Optional name for the constraint node.

    Returns:
        ActionResultModel with constraint node name.
    """
    target = str(params.get("target", ""))
    obj = str(params.get("object", ""))
    aim_vector = list(params.get("aim_vector", [1.0, 0.0, 0.0]))
    up_vector = list(params.get("up_vector", [0.0, 1.0, 0.0]))
    weight = float(params.get("weight", 1.0))
    name = str(params.get("name", ""))

    if not target or not obj:
        return error_result(
            "Invalid parameters",
            "Both 'target' and 'object' are required.",
        )

    try:
        kwargs: Dict[str, object] = {
            "aimVector": aim_vector,
            "upVector": up_vector,
            "weight": weight,
        }
        if name:
            kwargs["name"] = name

        result = cmds.tangentConstraint(target, obj, **kwargs)
        constraint_node = result[0] if isinstance(result, (list, tuple)) else result

        return success_result(
            "Created tangent constraint '{}' on '{}'".format(constraint_node, obj),
            prompt="Use pathAnimation on the object to move it along the curve while the tangent constraint maintains orientation.",
            constraint=constraint_node,
            target=target,
            object=obj,
        )
    except Exception as exc:
        return error_result("Failed to create tangent constraint", str(exc))
