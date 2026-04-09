"""Assign an object to an existing render layer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_render_layer(
    object_name: str,
    layer_name: str,
) -> dict:
    """Assign an object to an existing render layer.

    Args:
        object_name: Name of the object to assign.
        layer_name: Name of the target render layer.

    Returns:
        ActionResultModel dict with ``context.object_name`` and
        ``context.layer_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if not cmds.objExists(layer_name):
            return error_result(
                "Render layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        if cmds.objectType(layer_name) != "renderLayer":
            return error_result(
                "Not a render layer: {}".format(layer_name),
                "'{}' is of type '{}', expected 'renderLayer'".format(layer_name, cmds.objectType(layer_name)),
            ).to_dict()

        cmds.editRenderLayerMembers(layer_name, object_name, noRecurse=True)

        return success_result(
            "Assigned '{}' to render layer '{}'".format(object_name, layer_name),
            object_name=object_name,
            layer_name=layer_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_render_layer failed")
        return error_result(
            "Failed to assign '{}' to render layer '{}'".format(object_name, layer_name),
            str(exc),
        ).to_dict()


def main(**kwargs):
    return set_render_layer(**kwargs)


if __name__ == "__main__":
    import json

    result = set_render_layer()
    print(json.dumps(result))
