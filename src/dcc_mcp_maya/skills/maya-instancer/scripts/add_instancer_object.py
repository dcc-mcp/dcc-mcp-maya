"""Add an object to an existing Particle Instancer."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Add an instance object to an existing instancer.

    Args:
        params: Dictionary containing:
            - particle_system (str): Name of the particle/nParticle object. Required.
            - instancer (str): Name of the instancer node. Required.
            - object (str): Object to add as an instance. Required.

    Returns:
        ActionResultModel confirming the object was added.
    """
    particle_system = params.get("particle_system", "")
    instancer = params.get("instancer", "")
    obj = params.get("object", "")

    if not particle_system or not instancer or not obj:
        return error_result(
            "Invalid parameters",
            "Parameters 'particle_system', 'instancer', and 'object' are all required.",
        )

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
        cmds.particleInstancer(particle_system, edit=True, addObject=True, object=obj)
        return success_result(
            "Added '{}' to instancer '{}'".format(obj, instancer),
            prompt="Use list_instancers to verify the updated instance objects list.",
            instancer=instancer,
            added_object=obj,
        )
    except Exception as exc:
        return error_result("Failed to add object to instancer", str(exc))
