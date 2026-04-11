"""Add an additional geometry object to an existing instancer node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (particle_system, instancer_node, object_name):
            if not cmds.objExists(name):
                return maya_error(
                    "Node not found: {}".format(name),
                    "'{}' does not exist".format(name),
                )

        cmds.particleInstancer(
            particle_system,
            edit=True,
            addObject=True,
            object=[object_name],
            name=instancer_node,
        )

        return maya_success(
            "Added '{}' to instancer '{}'".format(object_name, instancer_node),
            prompt="Set a per-particle objectIndex attribute to control which shape each particle uses.",
            instancer_node=instancer_node,
            added_object=object_name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add instance object")


def main(**kwargs):
    return add_instance_object(**kwargs)


if __name__ == "__main__":
    import json

    result = add_instance_object("nParticle1", "instancer1", "pCube1")
    print(json.dumps(result, indent=2))
