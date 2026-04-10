"""Add a passive rigid body collider to the nCloth simulation."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Create a passive collider for nCloth interaction.

    Args:
        params: Dictionary with keys:
            - mesh (str): Transform node of the collider mesh.
            - friction (float): Surface friction [0, 1]. Default 0.1.
            - stickiness (float): Stickiness [0, 1]. Default 0.0.

    Returns:
        ActionResultModel with nRigid node name.
    """
    mesh = params.get("mesh", "")
    friction = params.get("friction", 0.1)
    stickiness = params.get("stickiness", 0.0)

    if not mesh:
        return error_result("Invalid parameter", "mesh must not be empty.")

    try:
        if not cmds.objExists(mesh):
            return error_result("Mesh not found", "'{0}' does not exist.".format(mesh))

        cmds.select(mesh, replace=True)
        result = cmds.nRigid()
        rigid_node = result[0] if result else ""

        cmds.setAttr("{0}.friction".format(rigid_node), max(0.0, min(1.0, friction)))
        cmds.setAttr("{0}.stickiness".format(rigid_node), max(0.0, min(1.0, stickiness)))

        return success_result(
            "Added passive collider from mesh '{0}'".format(mesh),
            prompt="Collider added. Simulate with simulate_cloth to see cloth interact with this object.",
            rigid_node=rigid_node,
            mesh=mesh,
            friction=friction,
            stickiness=stickiness,
        )
    except Exception as exc:
        return error_result("Failed to add cloth collider", str(exc))
