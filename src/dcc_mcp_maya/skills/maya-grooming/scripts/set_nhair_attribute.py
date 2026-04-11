"""Set an attribute on a Maya hairSystem node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_nhair_attribute(hair_system: str, attribute: str, value: float) -> dict:
    """Set a named attribute on a hairSystem node.

    Args:
        hair_system: Name of the hairSystem node.
        attribute: Attribute name (e.g. ``'stiffness'``, ``'damping'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(hair_system):
            return maya_error(
                "Node not found",
                "hairSystem '{}' does not exist".format(hair_system),
            )

        cmds.setAttr("{}.{}".format(hair_system, attribute), value)

        return maya_success(
            "nHair attribute set",
            prompt="hairSystem {}.{} = {}. Simulate to see the effect.".format(hair_system, attribute, value),
            hair_system=hair_system,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set nHair attribute")


def main(**kwargs):
    return set_nhair_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_nhair_attribute("hairSystem1", "stiffness", 0.8)
    print(json.dumps(result))
