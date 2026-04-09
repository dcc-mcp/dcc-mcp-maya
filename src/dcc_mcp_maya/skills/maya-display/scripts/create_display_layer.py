"""Create a display layer and optionally add objects to it."""

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



def main(**kwargs):
    return create_display_layer(**kwargs)


if __name__ == "__main__":
    import json
    result = create_display_layer()
    print(json.dumps(result))
