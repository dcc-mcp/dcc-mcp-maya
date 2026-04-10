"""Delete an Assembly Reference node from the scene."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Delete an assemblyReference node.

    Args:
        params: Dictionary containing:
            - assembly (str): Name of the assemblyReference node to delete. Required.

    Returns:
        ActionResultModel confirming deletion.
    """
    assembly = params.get("assembly", "")

    if not assembly:
        return error_result("Invalid parameters", "Parameter 'assembly' is required.")

    try:
        if not cmds.objExists(assembly):
            return error_result(
                "Assembly not found",
                "No node named '{}' in the scene.".format(assembly),
            )
        node_type = cmds.nodeType(assembly)
        if node_type != "assemblyReference":
            return error_result(
                "Invalid node type",
                "Node '{}' is '{}', expected 'assemblyReference'.".format(assembly, node_type),
            )
        cmds.delete(assembly)
        return success_result(
            "Deleted assembly reference '{}'".format(assembly),
            prompt="Use list_assemblies to verify the assembly was removed.",
            deleted_assembly=assembly,
        )
    except Exception as exc:
        return error_result("Failed to delete assembly reference", str(exc))
