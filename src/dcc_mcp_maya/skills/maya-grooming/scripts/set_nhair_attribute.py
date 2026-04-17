"""Set an attribute on a Maya hairSystem node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_nhair_attribute(hair_system: str, attribute: str, value: float) -> dict:
    """Set a named attribute on a hairSystem node.

    Args:
        hair_system: Name of the hairSystem node.
        attribute: Attribute name (e.g. ``'stiffness'``, ``'damping'``).
        value: Numeric value to set.

    Returns:
        ToolResult dict confirming the attribute change.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, hair_system)
        if err:
            return err

        cmds.setAttr("{}.{}".format(hair_system, attribute), value)

        return skill_success(
            "nHair attribute set",
            prompt="hairSystem {}.{} = {}. Simulate to see the effect.".format(hair_system, attribute, value),
            hair_system=hair_system,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set nHair attribute")


@skill_entry
def main(**kwargs):
    return set_nhair_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
