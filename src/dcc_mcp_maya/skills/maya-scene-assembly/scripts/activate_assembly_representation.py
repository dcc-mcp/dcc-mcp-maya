"""Activate a specific representation (LOD) on an Assembly Reference node."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Activate a named representation on an Assembly Reference node.

    Args:
        params: Dictionary containing:
            - assembly (str): Name of the assemblyReference node. Required.
            - representation (str): Name of the representation to activate. Required.

    Returns:
        ActionResultModel with the activated representation info.
    """
    assembly = params.get("assembly", "")
    representation = params.get("representation", "")

    if not assembly or not representation:
        return error_result(
            "Invalid parameters",
            "Both 'assembly' and 'representation' are required.",
        )

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
        cmds.assembly(assembly, edit=True, activeRepresentation=representation)
        return success_result(
            "Activated representation '{}' on '{}'".format(representation, assembly),
            prompt="Use list_assemblies to verify the active representation.",
            assembly=assembly,
            representation=representation,
        )
    except Exception as exc:
        return error_result("Failed to activate representation", str(exc))
