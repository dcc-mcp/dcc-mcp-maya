"""Set an attribute override on a render layer node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules


def set_render_layer_attribute(
    layer_name: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute override on a render layer node.

    Common attributes:
    - ``renderable`` (bool): whether the layer is included in batch render
    - ``color`` (list of 3 floats): layer identification colour in the UI

    Args:
        layer_name: Name of the render layer to modify.
        attribute: Attribute name on the ``renderLayer`` node.
        value: New value.  Scalar or list-of-3 floats for compound attrs.

    Returns:
        ActionResultModel dict with ``context.layer_name``,
        ``context.attribute``, and ``context.value``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(layer_name):
            return maya_error(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            )

        if cmds.objectType(layer_name) != "renderLayer":
            return maya_error(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}'".format(layer_name, cmds.objectType(layer_name)),
            )

        attr_path = "{}.{}".format(layer_name, attribute)

        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value, type="double3" if len(value) == 3 else "double4")
        elif isinstance(value, bool):
            cmds.setAttr(attr_path, int(value))
        else:
            cmds.setAttr(attr_path, value)

        return maya_success(
            "Set {}.{} = {}".format(layer_name, attribute, value),
            layer_name=layer_name,
            attribute=attribute,
            value=value,
            prompt="Use list_render_layers to verify the change.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set attribute '{}.{}'".format(layer_name, attribute))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_render_layer_attribute`."""
    return set_render_layer_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_render_layer_attribute()
    print(json.dumps(result))
