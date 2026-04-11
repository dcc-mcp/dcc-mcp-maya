"""Delete a display layer."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if layer_name == "defaultLayer":
            return maya_error(
                "Cannot delete defaultLayer",
                "The built-in 'defaultLayer' cannot be deleted",
            )

        if not cmds.objExists(layer_name):
            return maya_error(
                "Display layer not found: {}".format(layer_name),
                "'{}' does not exist".format(layer_name),
            )

        if cmds.objectType(layer_name) != "displayLayer":
            return maya_error(
                "Not a display layer: {}".format(layer_name),
                "'{}' is not a displayLayer node".format(layer_name),
            )

        deleted_objects = []
        if remove_objects:
            members = cmds.editDisplayLayerMembers(layer_name, query=True) or []
            if members:
                cmds.delete(*members)
                deleted_objects = list(members)

        cmds.delete(layer_name)

        return maya_success(
            "Deleted display layer '{}'{}".format(
                layer_name,
                " and {} object(s)".format(len(deleted_objects)) if deleted_objects else "",
            ),
            layer_name=layer_name,
            objects_deleted=deleted_objects,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete display layer '{}'".format(layer_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_display_layer`."""
    return delete_display_layer(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_display_layer()
    print(json.dumps(result))
