"""List all available representations for an Assembly Reference node."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """List all representations available on an Assembly Reference node.

    Args:
        params: Dictionary containing:
            - assembly (str): Name of the assemblyReference node. Required.

    Returns:
        ActionResultModel with list of representation names and the active one.
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
        reps: List[str] = cmds.assembly(assembly, query=True, listRepresentations=True) or []
        active_rep = cmds.assembly(assembly, query=True, activeRepresentation=True) or ""
        return success_result(
            "Found {} representation(s) for '{}'".format(len(reps), assembly),
            prompt="Use activate_assembly_representation to switch the active LOD.",
            assembly=assembly,
            representations=reps,
            active_representation=active_rep,
            count=len(reps),
        )
    except Exception as exc:
        return error_result("Failed to list representations", str(exc))
