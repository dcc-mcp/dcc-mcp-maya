"""Set an attribute on a Maya light node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def set_light_attribute(
    light_name: str,
    attribute: str,
    value: object,
) -> dict:
    """Set a named attribute on a Maya light.

    Common attributes: ``intensity``, ``colorR``, ``colorG``, ``colorB``,
    ``useRayTraceShadows``, ``shadowColor``, ``penumbraAngle`` (spotLight),
    ``decayRate``.

    Args:
        light_name: Name of the light transform or shape node.
        attribute: Attribute name.
        value: New value.

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_name):
            return maya_error(
                "Light not found: {}".format(light_name),
                "'{}' does not exist".format(light_name),
            )

        # Resolve shape if transform supplied
        node_type = cmds.objectType(light_name)
        if node_type == "transform":
            shapes = cmds.listRelatives(light_name, shapes=True) or []
            if not shapes:
                return maya_error(
                    "No shape under '{}'".format(light_name),
                    "Cannot find a light shape node",
                )
            light_node = shapes[0]
        else:
            light_node = light_name

        full_attr = "{}.{}".format(light_node, attribute)
        if isinstance(value, (list, tuple)):
            cmds.setAttr(full_attr, *value)
        else:
            cmds.setAttr(full_attr, value)

        return maya_success(
            "Set {}.{} = {}".format(light_node, attribute, value),
            prompt="Use list_lights to see all lights in the scene.",
            light_name=light_node,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set light attribute")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_light_attribute`."""
    return set_light_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_light_attribute("pointLight1", "intensity", 3.0)
    print(json.dumps(result))
