"""Add a new target mesh to an existing blend shape node."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Add a new target mesh to an existing blend shape deformer.

    Args:
        params: Dictionary with keys:
            - blend_shape (str): Existing blend shape node name. Required.
            - target (str): Mesh to use as the blend target. Required.
            - weight (float): Initial weight (0.0–1.0). Default 0.0.
            - index (int): Target index slot. Auto-assigned if omitted.

    Returns:
        ActionResultModel with the new target index.
    """
    bs_node = params.get("blend_shape", "")
    target = params.get("target", "")
    weight = float(params.get("weight", 0.0))
    index = params.get("index", None)

    if not bs_node:
        return error_result("Missing required parameter", "Parameter 'blend_shape' is required")
    if not target:
        return error_result("Missing required parameter", "Parameter 'target' is required")

    try:
        bs_node = str(bs_node)
        target = str(target)

        if not cmds.objExists(bs_node):
            return error_result("Node not found", "Blend shape '{}' does not exist".format(bs_node))
        if not cmds.objExists(target):
            return error_result("Target not found", "Mesh '{}' does not exist".format(target))

        # Determine next index
        if index is None:
            aliases = cmds.aliasAttr(bs_node, query=True) or []
            index = len(aliases) // 2

        cmds.blendShape(
            bs_node, edit=True,
            target=[cmds.blendShape(bs_node, query=True, geometry=True)[0], int(index), target, 1.0],
            weight=[int(index), weight],
        )

        return success_result(
            "Added blend target '{}' at index {}".format(target, index),
            prompt="Use set_blend_shape_weight to animate this target's weight.",
            blend_shape_node=bs_node,
            target=target,
            index=int(index),
            initial_weight=weight,
        )
    except Exception as exc:
        return error_result("Failed to add blend shape target", str(exc))
