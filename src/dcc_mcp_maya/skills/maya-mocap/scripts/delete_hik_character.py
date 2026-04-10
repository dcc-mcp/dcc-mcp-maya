"""Delete a HumanIK character node and optionally its retargeters."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Delete a HIKCharacterNode and optionally connected retargeters.

    Args:
        params: Dictionary with keys:
            - character_node (str): HIKCharacterNode to delete.
            - delete_retargeters (bool): Also delete connected HIKRetargeter nodes. Default True.

    Returns:
        ActionResultModel with deletion result.
    """
    char_node = params.get("character_node", "")
    delete_retargeters = params.get("delete_retargeters", True)

    if not char_node:
        return error_result("Invalid parameter", "character_node must not be empty.")

    try:
        if not cmds.objExists(char_node):
            return error_result(
                "Node not found: '{0}'".format(char_node),
                "HIKCharacterNode does not exist in the scene.",
            )
        if cmds.nodeType(char_node) != "HIKCharacterNode":
            return error_result(
                "Invalid node type",
                "Expected HIKCharacterNode, got {0}.".format(cmds.nodeType(char_node)),
            )

        deleted = [char_node]

        if delete_retargeters:
            # Find retargeters connected to this character
            connections = cmds.listConnections(char_node, type="HIKRetargeter") or []
            for retargeter in set(connections):
                if cmds.objExists(retargeter):
                    cmds.delete(retargeter)
                    deleted.append(retargeter)

        cmds.delete(char_node)

        return success_result(
            "Deleted HIK character '{0}' and {1} retargeter(s)".format(
                char_node, len(deleted) - 1
            ),
            prompt="Character removed. Use create_hik_character to set up a new one.",
            deleted_nodes=deleted,
        )
    except Exception as exc:
        return error_result("Failed to delete HIK character", str(exc))
