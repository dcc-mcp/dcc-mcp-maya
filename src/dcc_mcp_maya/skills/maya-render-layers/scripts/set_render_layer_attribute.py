"""Set an attribute override on a render layer node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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

        err = validate_node_exists(cmds, layer_name)
        if err:
            return err

        if cmds.objectType(layer_name) != "renderLayer":
            return skill_error(
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

        return skill_success(
            "Set {}.{} = {}".format(layer_name, attribute, value),
            layer_name=layer_name,
            attribute=attribute,
            value=value,
            prompt="Use list_render_layers to verify the change.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set attribute '{}.{}'".format(layer_name, attribute))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_render_layer_attribute`."""
    return set_render_layer_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
