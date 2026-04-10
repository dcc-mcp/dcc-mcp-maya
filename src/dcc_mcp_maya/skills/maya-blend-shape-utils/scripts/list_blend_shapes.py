"""List all blend shape nodes in the scene."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """List all blendShape nodes with their targets and driven geometry.

    Args:
        params: Dictionary with keys:
            - mesh (str): Optional mesh name to filter by driven geometry.

    Returns:
        ActionResultModel with list of blend shape node info.
    """
    mesh = params.get("mesh", "")

    try:
        if mesh:
            history = cmds.listHistory(str(mesh)) or []
            all_bs = [n for n in history if cmds.objectType(n) == "blendShape"]
        else:
            all_bs = cmds.ls(type="blendShape") or []

        result: List[Dict[str, object]] = []
        for bs_node in all_bs:
            driven = cmds.blendShape(bs_node, query=True, geometry=True) or []
            aliases = cmds.aliasAttr(bs_node, query=True) or []
            target_names: List[str] = [aliases[i] for i in range(0, len(aliases), 2)]
            result.append({
                "node": bs_node,
                "driven": list(driven),
                "targets": target_names,
                "target_count": len(target_names),
            })

        return success_result(
            "Found {} blend shape node(s)".format(len(result)),
            prompt="Use get_blend_shape_weights to inspect weights on a specific node.",
            blend_shapes=result,
            count=len(result),
        )
    except Exception as exc:
        return error_result("Failed to list blend shapes", str(exc))
