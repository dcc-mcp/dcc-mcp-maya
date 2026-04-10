"""Set a blend shape target weight."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Set a blend shape target weight by name or index.

    Args:
        params: Dictionary with keys:
            - blend_shape (str): Blend shape node name. Required.
            - target (str): Target alias name. Required unless index is given.
            - index (int): Target index (0-based). Used if target not given.
            - weight (float): Weight value (0.0–1.0). Required.

    Returns:
        ActionResultModel with new weight value.
    """
    bs_node = params.get("blend_shape", "")
    target = params.get("target", "")
    index = params.get("index", None)
    weight = params.get("weight", None)

    if not bs_node:
        return error_result("Missing required parameter", "Parameter 'blend_shape' is required")
    if weight is None:
        return error_result("Missing required parameter", "Parameter 'weight' is required")
    if not target and index is None:
        return error_result(
            "Missing required parameter", "Either 'target' or 'index' must be provided"
        )

    try:
        bs_node = str(bs_node)
        if not cmds.objExists(bs_node):
            return error_result("Node not found", "Blend shape node '{}' does not exist".format(bs_node))

        if target:
            attr = "{}.{}".format(bs_node, str(target))
            if not cmds.objExists(attr):
                return error_result(
                    "Target not found", "Target '{}' not found on '{}'".format(target, bs_node)
                )
            cmds.setAttr(attr, float(weight))
            used_target = str(target)
        else:
            cmds.blendShape(bs_node, edit=True, weight=[int(index), float(weight)])
            used_target = "index_{}".format(index)

        return success_result(
            "Set blend shape weight: {} = {:.4f}".format(used_target, float(weight)),
            prompt="Use get_blend_shape_weights to verify all target weights.",
            blend_shape_node=bs_node,
            target=used_target,
            weight=float(weight),
        )
    except Exception as exc:
        return error_result("Failed to set blend shape weight", str(exc))
