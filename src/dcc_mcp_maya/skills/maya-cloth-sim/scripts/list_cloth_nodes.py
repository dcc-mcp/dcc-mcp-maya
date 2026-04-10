"""List all nCloth nodes in the current scene."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """List all nCloth nodes in the scene.

    Args:
        params: Unused.

    Returns:
        ActionResultModel with list of nCloth info dicts.
    """
    try:
        cloth_nodes = cmds.ls(type="nCloth") or []
        info = []
        for node in cloth_nodes:
            entry = {"node": node}
            for attr in ("thickness", "stretchResistance", "bendResistance", "mass"):
                if cmds.attributeQuery(attr, node=node, exists=True):
                    entry[attr] = cmds.getAttr("{0}.{1}".format(node, attr))
            info.append(entry)

        return success_result(
            "Found {0} nCloth node(s) in scene".format(len(info)),
            prompt="Use set_cloth_attribute to change simulation parameters, or simulate_cloth to run the sim.",
            cloth_nodes=info,
            count=len(info),
        )
    except Exception as exc:
        return error_result("Failed to list cloth nodes", str(exc))
