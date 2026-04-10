"""Set attributes on an nParticle shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(particle_shape):
            return error_result(
                "nParticle shape '{}' not found".format(particle_shape),
                "Use list_nparticle_systems to find available nParticle nodes",
            ).to_dict()

        if cmds.objectType(particle_shape) != "nParticle":
            return error_result(
                "'{}' is not an nParticle node".format(particle_shape),
                "Provide the name of an nParticle shape node",
            ).to_dict()

        full_attr = "{}.{}".format(particle_shape, attribute)
        if not cmds.attributeQuery(attribute, node=particle_shape, exists=True):
            return error_result(
                "Attribute '{}' does not exist on '{}'".format(attribute, particle_shape),
                "Check attribute name spelling",
            ).to_dict()

        cmds.setAttr(full_attr, value)
        actual = cmds.getAttr(full_attr)

        return success_result(
            "Set {}.{} = {}".format(particle_shape, attribute, value),
            prompt="Use list_nparticle_systems to inspect all particle node settings.",
            particle_shape=particle_shape,
            attribute=attribute,
            value=actual,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_nparticle_attribute failed")
        return error_result(
            "Failed to set attribute '{}'".format(attribute), str(exc)
        ).to_dict()


def main(**kwargs):
    return set_nparticle_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_nparticle_attribute("nParticleShape1", "radius", 0.2)))
