"""Delete an nParticle system from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_nparticle_system(particle_node: str, delete_nucleus: bool = False) -> dict:
    """Delete an nParticle object and optionally its nucleus solver.

    Args:
        particle_node: Name of the nParticle object to delete.
        delete_nucleus: If ``True``, also delete the connected nucleus solver
            (only if no other nParticle objects are connected to it).

    Returns:
        ActionResultModel dict with ``context.particle_node`` and
        ``context.nucleus_deleted``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not particle_node:
        return error_result("Invalid particle_node", "particle_node must not be empty").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(particle_node):
            return error_result(
                "nParticle node not found: '{}'".format(particle_node),
                "Use list_nparticle_systems to see available nodes.",
            ).to_dict()

        nucleus_deleted = False
        nucleus_node = None

        if delete_nucleus:
            connections = cmds.listConnections(particle_node, type="nucleus") or []
            if connections:
                nucleus_node = connections[0]

        cmds.delete(particle_node)

        if delete_nucleus and nucleus_node:
            # Only delete nucleus if no other nParticle nodes remain connected
            remaining = cmds.listConnections(nucleus_node, type="nParticle") or []
            if not remaining:
                cmds.delete(nucleus_node)
                nucleus_deleted = True

        return success_result(
            "Deleted nParticle system '{}'".format(particle_node),
            prompt="nParticle system removed. Use create_nparticle_system to create a new one.",
            particle_node=particle_node,
            nucleus_deleted=nucleus_deleted,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_nparticle_system failed")
        return error_result("Failed to delete nParticle system", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_nparticle_system(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_nparticle_system("nParticle1")))
