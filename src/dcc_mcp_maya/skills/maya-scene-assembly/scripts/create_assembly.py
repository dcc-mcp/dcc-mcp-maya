"""Create a Scene Assembly Reference node."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Create an Assembly Reference node.

    Args:
        params: Dictionary containing:
            - name (str): Name for the assembly node. Required.
            - definition (str): Path to the Assembly Definition file (.ad). Optional.

    Returns:
        ActionResultModel with the created assembly node name.
    """
    name = params.get("name", "")
    definition = params.get("definition", "")

    if not name:
        return error_result("Invalid parameters", "Parameter 'name' is required.")

    try:
        assembly_node = cmds.assembly(name=name, type="assemblyReference")
        if definition:
            cmds.setAttr("{}.definition".format(assembly_node), definition, type="string")
        return success_result(
            "Created assembly reference '{}'".format(assembly_node),
            prompt="Use activate_assembly_representation to switch LOD representations.",
            assembly_node=assembly_node,
        )
    except Exception as exc:
        return error_result("Failed to create assembly reference", str(exc))
