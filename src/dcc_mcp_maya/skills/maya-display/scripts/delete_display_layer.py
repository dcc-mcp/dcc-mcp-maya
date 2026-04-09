"""Delete a display layer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_display_layer(
    layer_name: str,
    remove_objects: bool = False,
) -> dict:
    """Delete a display layer.

    Args:
        layer_name: Name of the display layer to delete.  The built-in
            ``"defaultLayer"`` cannot be deleted and will cause an error.
        remove_objects: If True, also delete all objects that were members of
            this layer.  Default: False (objects are moved to the default layer).

    Returns:
        ActionResultModel dict with ``context.layer_name`` and
        ``context.objects_deleted`` (when ``remove_objects=True``).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if layer_name == "defaultLayer":
            return error_result(
                "Cannot delete defaultLayer",
                "The built-in 'defaultLayer' cannot be deleted",
            ).to_dict()

        if not cmds.objExists(layer_name):
            return error_result(
                "Display layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            ).to_dict()

        if cmds.objectType(layer_name) != "displayLayer":
            return error_result(
                "Not a display layer: {}".format(layer_name),
                "'{}' is not a displayLayer node".format(layer_name),
            ).to_dict()

        deleted_objects = []
        if remove_objects:
            members = cmds.editDisplayLayerMembers(layer_name, query=True) or []
            if members:
                cmds.delete(*members)
                deleted_objects = list(members)

        cmds.delete(layer_name)

        return success_result(
            "Deleted display layer '{}'{}".format(
                layer_name,
                " and {} object(s)".format(len(deleted_objects)) if deleted_objects else "",
            ),
            layer_name=layer_name,
            objects_deleted=deleted_objects,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_display_layer failed")
        return error_result("Failed to delete display layer '{}'".format(layer_name), str(exc)).to_dict()


def main(**kwargs):
    return delete_display_layer(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_display_layer()
    print(json.dumps(result))
