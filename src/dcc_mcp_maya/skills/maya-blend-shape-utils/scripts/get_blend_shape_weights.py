"""Get blend shape target weights for a mesh."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Get all blend shape target weights for a mesh or blend shape node.

    Args:
        params: Dictionary with keys:
            - mesh (str): Mesh or blend shape node name. Required.

    Returns:
        ActionResultModel with target names and weight values.
    """
    mesh = params.get("mesh", "")
    if not mesh:
        return error_result("Missing required parameter", "Parameter 'mesh' is required")

    try:
        # Resolve blend shape node
        if cmds.objectType(str(mesh)) == "blendShape":
            bs_node = str(mesh)
        else:
            history = cmds.listHistory(str(mesh)) or []
            bs_nodes = [n for n in history if cmds.objectType(n) == "blendShape"]
            if not bs_nodes:
                return error_result(
                    "No blend shape found", "No blendShape deformer on: {}".format(mesh)
                )
            bs_node = bs_nodes[0]

        # Get target aliases and weights
        aliases = cmds.aliasAttr(bs_node, query=True) or []
        targets: List[Dict[str, object]] = []
        for i in range(0, len(aliases), 2):
            alias_name = aliases[i]
            attr_name = aliases[i + 1]
            weight_val = cmds.getAttr("{}.{}".format(bs_node, alias_name))
            targets.append({"name": alias_name, "attr": attr_name, "weight": weight_val})

        return success_result(
            "Got {} blend shape weights from '{}'".format(len(targets), bs_node),
            prompt="Use set_blend_shape_weight to change individual target weights.",
            blend_shape_node=bs_node,
            targets=targets,
            count=len(targets),
        )
    except Exception as exc:
        return error_result("Failed to get blend shape weights", str(exc))
