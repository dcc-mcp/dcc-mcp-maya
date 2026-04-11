"""Maya display layer management actions.

Provides actions to create, populate, query and delete display layers,
giving an Agent control over object visibility and display overrides.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists


def create_display_layer(
    name: str,
    objects: Optional[List[str]] = None,
    visible: bool = True,
    display_type: int = 0,
) -> dict:
    """Create a display layer and optionally add objects to it.

    Args:
        name: Name for the new display layer.
        objects: Optional list of object names to add to the layer immediately.
            If None or empty, an empty layer is created.
        visible: Initial visibility of the layer.  Default: True.
        display_type: Display override type for objects in this layer.
            ``0`` = Normal, ``1`` = Template, ``2`` = Reference.  Default: 0.

    Returns:
        ActionResultModel dict with ``context.layer_name``,
        ``context.objects_added``, ``context.visible``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415


        if not name or not name.strip():
            return skill_error("Invalid layer name", "name must not be empty")

        if display_type not in (0, 1, 2):
            return skill_error(
                "Invalid display_type: {}".format(display_type),
                "display_type must be 0 (Normal), 1 (Template) or 2 (Reference)",
            )

        # Validate objects first
        objects_to_add = list(objects) if objects else []
        err = batch_validate_nodes(cmds, list(objects_to_add))
        if err:
            return err

        layer = cmds.createDisplayLayer(name=name, empty=True)

        # Set visibility and display type
        cmds.setAttr("{}.visibility".format(layer), visible)
        cmds.setAttr("{}.displayType".format(layer), display_type)

        if objects_to_add:
            cmds.editDisplayLayerMembers(layer, *objects_to_add, noRecurse=True)

        return skill_success(
            "Created display layer '{}' with {} object(s)".format(layer, len(objects_to_add)),
            layer_name=layer,
            objects_added=objects_to_add,
            visible=visible,
            display_type=display_type,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create display layer '{}'".format(name))


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        err = validate_node_exists(cmds, layer_name)
        if err:
            return err

        # Verify it is actually a displayLayer node
        if cmds.objectType(layer_name) != "displayLayer":
            return skill_error(
                "Not a display layer: {}".format(layer_name),
                "'{}' is of type '{}', expected 'displayLayer'".format(layer_name, cmds.objectType(layer_name)),
            )

        cmds.editDisplayLayerMembers(layer_name, object_name, noRecurse=True)

        return skill_success(
            "Assigned '{}' to display layer '{}'".format(object_name, layer_name),
            object_name=object_name,
            layer_name=layer_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to assign '{}' to layer '{}'".format(object_name, layer_name))


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
            return skill_error(
                "Cannot delete defaultLayer",
                "The built-in 'defaultLayer' cannot be deleted",
            )

        err = validate_node_exists(cmds, layer_name)
        if err:
            return err

        if cmds.objectType(layer_name) != "displayLayer":
            return skill_error(
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

        return skill_success(
            "Deleted display layer '{}'{}".format(
                layer_name,
                " and {} object(s)".format(len(deleted_objects)) if deleted_objects else "",
            ),
            layer_name=layer_name,
            objects_deleted=deleted_objects,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete display layer '{}'".format(layer_name))


def list_display_layers() -> dict:
    """List all display layers in the scene.

    Returns:
        ActionResultModel dict with ``context.layers`` — a list of dicts
        with ``name``, ``visible``, ``display_type``, and ``member_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        layer_nodes = cmds.ls(type="displayLayer") or []
        layers = []
        for layer in layer_nodes:
            members = cmds.editDisplayLayerMembers(layer, query=True) or []
            layers.append(
                {
                    "name": layer,
                    "visible": bool(cmds.getAttr("{}.visibility".format(layer))),
                    "display_type": int(cmds.getAttr("{}.displayType".format(layer))),
                    "member_count": len(members),
                }
            )

        return skill_success(
            "Found {} display layer(s)".format(len(layers)),
            layers=layers,
            count=len(layers),
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list display layers")
