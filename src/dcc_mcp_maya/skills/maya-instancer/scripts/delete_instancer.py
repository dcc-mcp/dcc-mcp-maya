"""Delete a Particle Instancer node."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Delete an instancer node from the scene.

    Args:
        params: Dictionary containing:
            - instancer (str): Name of the instancer node to delete. Required.

    Returns:
        ActionResultModel confirming deletion.
    """
    instancer = params.get("instancer", "")

    if not instancer:
        return error_result("Invalid parameters", "Parameter 'instancer' is required.")

    try:
        if not cmds.objExists(instancer):
            return error_result(
                "Instancer not found",
                "No node named '{}' in the scene.".format(instancer),
            )
        if cmds.nodeType(instancer) != "instancer":
            return error_result(
                "Invalid node type",
                "Node '{}' is not an instancer.".format(instancer),
            )
        cmds.delete(instancer)
        return success_result(
            "Deleted instancer '{}'".format(instancer),
            prompt="Use list_instancers to verify the instancer was removed.",
            deleted_instancer=instancer,
        )
    except Exception as exc:
        return error_result("Failed to delete instancer", str(exc))
