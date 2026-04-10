"""Zero out all blend shape target weights."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Set all blend shape target weights to 0.0 on a blend shape node.

    Args:
        params: Dictionary with keys:
            - blend_shape (str): Blend shape node name. Required.

    Returns:
        ActionResultModel with count of zeroed targets.
    """
    bs_node = params.get("blend_shape", "")
    if not bs_node:
        return error_result("Missing required parameter", "Parameter 'blend_shape' is required")

    try:
        bs_node = str(bs_node)
        if not cmds.objExists(bs_node):
            return error_result("Node not found", "Blend shape '{}' does not exist".format(bs_node))

        aliases = cmds.aliasAttr(bs_node, query=True) or []
        target_names = [aliases[i] for i in range(0, len(aliases), 2)]

        for t_name in target_names:
            cmds.setAttr("{}.{}".format(bs_node, t_name), 0.0)

        return success_result(
            "Zeroed {} blend shape weights on '{}'".format(len(target_names), bs_node),
            prompt="Blend shape is now in neutral pose. Use set_blend_shape_weight to activate targets.",
            blend_shape_node=bs_node,
            zeroed_count=len(target_names),
            targets=target_names,
        )
    except Exception as exc:
        return error_result("Failed to zero blend shape weights", str(exc))
