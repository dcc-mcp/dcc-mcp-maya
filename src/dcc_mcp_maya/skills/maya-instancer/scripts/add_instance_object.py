"""Add an additional geometry object to an existing instancer node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def add_instance_object(
    particle_system: str,
    instancer_node: str,
    object_name: str,
) -> dict:
    """Add a geometry object to an existing particle instancer.

    The new object becomes available as an additional instance index that
    can be driven by a per-particle ``objectIndex`` attribute.

    Args:
        particle_system: Name of the particle system the instancer is attached to.
        instancer_node: Name of the existing ``instancer`` node.
        object_name: Transform node to add as an instance shape.

    Returns:
        ActionResultModel dict with the updated ``context.instancer_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (particle_system, instancer_node, object_name):
            if not cmds.objExists(name):
                return error_result(
                    "Node not found: {}".format(name),
                    "'{}' does not exist".format(name),
                ).to_dict()

        cmds.particleInstancer(
            particle_system,
            edit=True,
            addObject=True,
            object=[object_name],
            name=instancer_node,
        )

        return success_result(
            "Added '{}' to instancer '{}'".format(object_name, instancer_node),
            prompt="Set a per-particle objectIndex attribute to control which shape each particle uses.",
            instancer_node=instancer_node,
            added_object=object_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_instance_object failed")
        return error_result("Failed to add instance object", str(exc)).to_dict()


def main(**kwargs):
    return add_instance_object(**kwargs)


if __name__ == "__main__":
    import json

    result = add_instance_object("nParticle1", "instancer1", "pCube1")
    print(json.dumps(result, indent=2))
