"""Add an additional geometry object to an existing instancer node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
            err = validate_node_exists(cmds, name)
            if err:
                return err

        cmds.particleInstancer(
            particle_system,
            edit=True,
            addObject=True,
            object=[object_name],
            name=instancer_node,
        )

        return skill_success(
            "Added '{}' to instancer '{}'".format(object_name, instancer_node),
            prompt="Set a per-particle objectIndex attribute to control which shape each particle uses.",
            instancer_node=instancer_node,
            added_object=object_name,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add instance object")


@skill_entry
def main(**kwargs):
    return add_instance_object(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
