"""Assign an object to an existing display layer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


def set_display_layer(layer_name: str, objects: List[str]) -> dict:
    """Assign one or more objects to an existing display layer.

    Args:
        layer_name: Name of the target display layer.
        objects: List of object names to assign.

    Returns:
        ActionResultModel dict with ``context.assigned``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(layer_name):
            return error_result(
                "Display layer not found",
                "Layer '{}' does not exist in the scene".format(layer_name),
            ).to_dict()

        assigned = []
        missing = []
        for obj in objects:
            if cmds.objExists(obj):
                cmds.editDisplayLayerMembers(layer_name, obj, noRecurse=True)
                assigned.append(obj)
            else:
                missing.append(obj)

        msg = "Assigned {} object(s) to layer '{}'".format(len(assigned), layer_name)
        if missing:
            msg += "; {} not found: {}".format(len(missing), missing)

        return success_result(
            msg,
            prompt="Use list_display_layers to verify the layer membership.",
            layer_name=layer_name,
            assigned=assigned,
            missing=missing,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_display_layer failed")
        return error_result("Failed to assign objects to layer '{}'".format(layer_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_display_layer`."""
    return set_display_layer(**kwargs)


if __name__ == "__main__":
    import json

    result = set_display_layer("defaultLayer", ["pSphere1"])
    print(json.dumps(result))
