"""Maya display layer management actions.

Provides actions to create, populate, query and delete display layers,
giving an Agent control over object visibility and display overrides.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not name.strip():
            return error_result("Invalid layer name", "name must not be empty").to_dict()

        if display_type not in (0, 1, 2):
            return error_result(
                "Invalid display_type: {}".format(display_type),
                "display_type must be 0 (Normal), 1 (Template) or 2 (Reference)",
            ).to_dict()

        # Validate objects first
        objects_to_add = list(objects) if objects else []
        missing = [obj for obj in objects_to_add if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(missing),
                "The following objects do not exist in the scene: {}".format(missing),
            ).to_dict()

        layer = cmds.createDisplayLayer(name=name, empty=True)

        # Set visibility and display type
        cmds.setAttr("{}.visibility".format(layer), visible)
        cmds.setAttr("{}.displayType".format(layer), display_type)

        if objects_to_add:
            cmds.editDisplayLayerMembers(layer, *objects_to_add, noRecurse=True)

        return success_result(
            "Created display layer '{}' with {} object(s)".format(layer, len(objects_to_add)),
            layer_name=layer,
            objects_added=objects_to_add,
            visible=visible,
            display_type=display_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_display_layer failed")
        return error_result("Failed to create display layer '{}'".format(name), str(exc)).to_dict()


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


def list_display_layers() -> dict:
    """List all display layers in the scene.

    Returns:
        ActionResultModel dict with ``context.layers`` — a list of dicts
        with ``name``, ``visible``, ``display_type``, and ``member_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Found {} display layer(s)".format(len(layers)),
            layers=layers,
            count=len(layers),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_display_layers failed")
        return error_result("Failed to list display layers", str(exc)).to_dict()
