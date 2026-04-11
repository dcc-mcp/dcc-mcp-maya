"""Set an attribute on a Maya fluid shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_fluid_attribute(fluid_shape: str, attribute: str, value: float) -> dict:
    """Set a named attribute on a fluidShape node.

    Args:
        fluid_shape: Name of the fluidShape node.
        attribute: Attribute name (e.g. ``'density'``, ``'velocityX'``).
        value: Numeric value to set.

    Returns:
        ActionResultModel dict confirming the attribute change.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(fluid_shape):
            return error_result(
                "Node not found",
                "fluidShape '{}' does not exist".format(fluid_shape),
            ).to_dict()

        cmds.setAttr("{}.{}".format(fluid_shape, attribute), value)

        return success_result(
            "Fluid attribute set",
            prompt="Attribute {}.{} updated. Simulate to see the effect.".format(fluid_shape, attribute),
            fluid_shape=fluid_shape,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_fluid_attribute failed")
        return error_result("Failed to set fluid attribute", str(exc)).to_dict()


def main(**kwargs):
    return set_fluid_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_fluid_attribute("fluidShape1", "density", 0.5)
    print(json.dumps(result))
