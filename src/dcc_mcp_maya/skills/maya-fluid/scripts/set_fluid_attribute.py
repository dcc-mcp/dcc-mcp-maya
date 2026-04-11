"""Set an attribute on a Maya fluid shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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

        if not cmds.objExists(fluid_shape):
            return maya_error(
                "Node not found",
                "fluidShape '{}' does not exist".format(fluid_shape),
            )

        cmds.setAttr("{}.{}".format(fluid_shape, attribute), value)

        return maya_success(
            "Fluid attribute set",
            prompt="Attribute {}.{} updated. Simulate to see the effect.".format(fluid_shape, attribute),
            fluid_shape=fluid_shape,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set fluid attribute")


def main(**kwargs):
    return set_fluid_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_fluid_attribute("fluidShape1", "density", 0.5)
    print(json.dumps(result))
