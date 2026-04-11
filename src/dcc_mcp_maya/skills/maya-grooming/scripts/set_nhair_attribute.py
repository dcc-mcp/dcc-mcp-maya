"""Set an attribute on a Maya hairSystem node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_nhair_attribute(hair_system: str, attribute: str, value: float) -> dict:
    """Set a named attribute on a hairSystem node.

    Args:
        hair_system: Name of the hairSystem node.
        attribute: Attribute name (e.g. ``'stiffness'``, ``'damping'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(hair_system):
            return error_result(
                "Node not found",
                "hairSystem '{}' does not exist".format(hair_system),
            ).to_dict()

        cmds.setAttr("{}.{}".format(hair_system, attribute), value)

        return success_result(
            "nHair attribute set",
            prompt="hairSystem {}.{} = {}. Simulate to see the effect.".format(hair_system, attribute, value),
            hair_system=hair_system,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_nhair_attribute failed")
        return error_result("Failed to set nHair attribute", str(exc)).to_dict()


def main(**kwargs):
    return set_nhair_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_nhair_attribute("hairSystem1", "stiffness", 0.8)
    print(json.dumps(result))
