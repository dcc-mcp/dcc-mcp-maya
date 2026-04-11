"""Delete a display layer."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import (
    maya_error,
    maya_from_exception,
    maya_success,
    validate_node_exists,
    validate_node_type,
)


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

        err = validate_node_exists(cmds, layer_name)
        if err:
            return err

        err = validate_node_type(cmds, layer_name, "displayLayer")
        if err:
            return err

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
            prompt="Use list_display_layers to confirm deletion.",
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
