"""Set attributes on an nParticle shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_nparticle_attribute(
    particle_shape: str,
    attribute: str,
    value: object,
) -> dict:
    """Set a single attribute on an nParticle shape node.

    Common attributes: ``radius``, ``mass``, ``conserve``, ``drag``,
    ``damp``, ``lifespanMode``, ``lifespan``, ``lifespanRandom``.

    Args:
        particle_shape: Name of the ``nParticle`` shape node.
        attribute: Attribute name to set.
        value: New value (float, int, or bool).

    Returns:
        ToolResult dict confirming the attribute change.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, particle_shape)
        if err:
            return err

        if cmds.objectType(particle_shape) != "nParticle":
            return skill_error(
                "'{}' is not an nParticle node".format(particle_shape),
                "Provide the name of an nParticle shape node",
            )

        full_attr = "{}.{}".format(particle_shape, attribute)
        if not cmds.attributeQuery(attribute, node=particle_shape, exists=True):
            return skill_error(
                "Attribute '{}' does not exist on '{}'".format(attribute, particle_shape),
                "Check attribute name spelling",
            )

        cmds.setAttr(full_attr, value)
        actual = cmds.getAttr(full_attr)

        return skill_success(
            "Set {}.{} = {}".format(particle_shape, attribute, value),
            prompt="Use list_nparticle_systems to inspect all particle node settings.",
            particle_shape=particle_shape,
            attribute=attribute,
            value=actual,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set attribute '{}'".format(attribute))


@skill_entry
def main(**kwargs):
    return set_nparticle_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
