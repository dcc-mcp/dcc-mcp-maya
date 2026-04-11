"""Set attributes on an nParticle shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
        ActionResultModel dict confirming the attribute change.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(particle_shape):
            return maya_error(
                "nParticle shape '{}' not found".format(particle_shape),
                "Use list_nparticle_systems to find available nParticle nodes",
            )

        if cmds.objectType(particle_shape) != "nParticle":
            return maya_error(
                "'{}' is not an nParticle node".format(particle_shape),
                "Provide the name of an nParticle shape node",
            )

        full_attr = "{}.{}".format(particle_shape, attribute)
        if not cmds.attributeQuery(attribute, node=particle_shape, exists=True):
            return maya_error(
                "Attribute '{}' does not exist on '{}'".format(attribute, particle_shape),
                "Check attribute name spelling",
            )

        cmds.setAttr(full_attr, value)
        actual = cmds.getAttr(full_attr)

        return maya_success(
            "Set {}.{} = {}".format(particle_shape, attribute, value),
            prompt="Use list_nparticle_systems to inspect all particle node settings.",
            particle_shape=particle_shape,
            attribute=attribute,
            value=actual,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set attribute '{}'".format(attribute))


def main(**kwargs):
    return set_nparticle_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_nparticle_attribute("nParticleShape1", "radius", 0.2)))
