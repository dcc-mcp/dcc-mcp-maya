"""Create a display layer and optionally add objects to it."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_display_layer(
    name: Optional[str] = None,
    objects: Optional[List[str]] = None,
    visibility: bool = True,
) -> dict:
    """Create a display layer and optionally add objects to it.

    Args:
        name: Name for the new display layer.  If None, Maya generates one.
        objects: List of object names to add to the layer immediately.
        visibility: Initial visibility state of the layer.

    Returns:
        ActionResultModel dict with ``context.layer_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"empty": True, "noRecurse": True}
        if name:
            kwargs["name"] = name
        layer_name = cmds.createDisplayLayer(**kwargs)

        if not visibility:
            cmds.setAttr("{}.visibility".format(layer_name), 0)

        added = []
        if objects:
            for obj in objects:
                if cmds.objExists(obj):
                    cmds.editDisplayLayerMembers(layer_name, obj, noRecurse=True)
                    added.append(obj)

        return success_result(
            "Created display layer '{}'".format(layer_name),
            prompt="Use set_display_layer to add more objects or list_display_layers to see all layers.",
            layer_name=layer_name,
            objects_added=added,
            visibility=visibility,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_display_layer failed")
        return error_result("Failed to create display layer", str(exc)).to_dict()


def main(**kwargs):
    return create_display_layer(**kwargs)


if __name__ == "__main__":
    import json

    result = create_display_layer()
    print(json.dumps(result))
