"""Set an attribute on a Maya nParticle object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any

logger = logging.getLogger(__name__)


def set_nparticle_attribute(
    particle_node: str,
    attribute: str,
    value: Any,
) -> dict:
    """Set an attribute on an nParticle node.

    Args:
        particle_node: Name of the nParticle object.
        attribute: Attribute name (e.g. ``"lifespanMode"``, ``"radius"``).
        value: New value for the attribute.

    Returns:
        ActionResultModel dict with ``context.particle_node``,
        ``context.attribute``, and ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not particle_node:
        return error_result("Invalid particle_node", "particle_node must not be empty").to_dict()
    if not attribute:
        return error_result("Invalid attribute", "attribute must not be empty").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(particle_node):
            return error_result(
                "nParticle node not found: '{}'".format(particle_node),
                "Use list_nparticle_systems to see available nodes.",
            ).to_dict()

        attr_path = "{}.{}".format(particle_node, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value)
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(particle_node, attribute, value),
            prompt="Attribute updated. Use list_nparticle_systems to verify changes.",
            particle_node=particle_node,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_nparticle_attribute failed")
        return error_result("Failed to set nParticle attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_nparticle_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_nparticle_attribute("nParticle1", "radius", 0.5)))
