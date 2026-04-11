"""Set an attribute on a Maya fluid shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_fluid_attribute(fluid_shape: str, attribute: str, value: float) -> dict:
    """Set a named attribute on a fluidShape node.

    Args:
        fluid_shape: Name of the fluidShape node.
        attribute: Attribute name (e.g. ``'density'``, ``'velocityX'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, fluid_shape)
        if err:
            return err

        cmds.setAttr("{}.{}".format(fluid_shape, attribute), value)

        return skill_success(
            "Fluid attribute set",
            prompt="Attribute {}.{} updated. Simulate to see the effect.".format(fluid_shape, attribute),
            fluid_shape=fluid_shape,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set fluid attribute")


@skill_entry
def main(**kwargs):
    return set_fluid_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
