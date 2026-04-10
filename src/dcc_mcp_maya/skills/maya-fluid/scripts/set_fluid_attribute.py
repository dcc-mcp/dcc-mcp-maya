"""Set an attribute on a Maya Fluid container."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

# Common fluid container attributes
_FLUID_ATTRS = {
    "densityMethod": "Density solver method (0=Off,1=Static,2=Dynamic)",
    "velocityMethod": "Velocity solver method",
    "temperatureMethod": "Temperature solver method",
    "fuelMethod": "Fuel solver method",
    "viscosity": "Fluid viscosity (0–1)",
    "friction": "Fluid friction against boundaries (0–1)",
    "dissipation": "Density dissipation rate per second",
    "buoyancy": "Upward force from temperature gradient",
    "turbulenceStrength": "Strength of turbulence force",
    "turbulenceFrequency": "Frequency of turbulence noise",
}


def set_fluid_attribute(fluid_node: str, attribute: str, value: object) -> dict:
    """Set an attribute on a Maya Fluid Effects container.

    Args:
        fluid_node: Name of the fluidShape or its transform.
        attribute: Attribute name (e.g. ``viscosity``, ``buoyancy``, ``dissipation``).
        value: New attribute value.

    Returns:
        ActionResultModel dict confirming the change.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not fluid_node or not attribute:
        return error_result(
            "fluid_node and attribute are required",
            "Provide the fluid node name and attribute.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(fluid_node):
            return error_result(
                "Fluid node '{}' does not exist".format(fluid_node),
                "Check the node name with list_fluid_containers.",
            ).to_dict()

        if not cmds.attributeQuery(attribute, node=fluid_node, exists=True):
            return error_result(
                "Attribute '{}' does not exist on '{}'".format(attribute, fluid_node),
                "Common attributes: {}".format(", ".join(_FLUID_ATTRS.keys())),
            ).to_dict()

        cmds.setAttr("{}.{}".format(fluid_node, attribute), value)

        return success_result(
            "Set {}.{} = {}".format(fluid_node, attribute, value),
            prompt="Attribute updated. Simulate to see the fluid dynamics change.",
            node=fluid_node,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_fluid_attribute failed")
        return error_result("Failed to set fluid attribute", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_fluid_attribute(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_fluid_attribute("fluidShape1", "viscosity", 0.5)))
