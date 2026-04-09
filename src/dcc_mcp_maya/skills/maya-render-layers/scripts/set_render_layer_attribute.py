"""Set an attribute override on a render layer node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(layer_name):
            return error_result(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        if cmds.objectType(layer_name) != "renderLayer":
            return error_result(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}'".format(layer_name, cmds.objectType(layer_name)),
            ).to_dict()

        attr_path = "{}.{}".format(layer_name, attribute)

        if isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value, type="double3" if len(value) == 3 else "double4")
        elif isinstance(value, bool):
            cmds.setAttr(attr_path, int(value))
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(layer_name, attribute, value),
            layer_name=layer_name,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_render_layer_attribute failed")
        return error_result("Failed to set attribute '{}.{}'".format(layer_name, attribute), str(exc)).to_dict()


def main(**kwargs):
    return set_render_layer_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_render_layer_attribute()
    print(json.dumps(result))
