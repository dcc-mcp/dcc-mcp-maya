"""Assign an object to an existing display layer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def set_display_layer(
    object_name: str,
    layer_name: str,
) -> dict:
    """Assign an object to an existing display layer.

    Args:
        object_name: Name of the Maya node to move.
        layer_name: Name of the target display layer.

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
                "Display layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        # Verify it is actually a displayLayer node
        if cmds.objectType(layer_name) != "displayLayer":
            return error_result(
                "Not a display layer: {}".format(layer_name),
                "'{}' is of type '{}', expected 'displayLayer'".format(layer_name, cmds.objectType(layer_name)),
            ).to_dict()

        cmds.editDisplayLayerMembers(layer_name, object_name, noRecurse=True)

        return success_result(
            "Assigned '{}' to display layer '{}'".format(object_name, layer_name),
            object_name=object_name,
            layer_name=layer_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_display_layer failed")
        return error_result("Failed to assign '{}' to layer '{}'".format(object_name, layer_name), str(exc)).to_dict()



def main(**kwargs):
    return set_display_layer(**kwargs)


if __name__ == "__main__":
    import json
    result = set_display_layer()
    print(json.dumps(result))
