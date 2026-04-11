"""Remove vertex colors from a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def remove_vertex_colors(object_name: str, color_set: Optional[str] = None) -> dict:
    """Remove vertex colors from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        color_set: Specific color set to remove.  If None, removes all
            vertex color data from the mesh.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name), "'{}' does not exist".format(object_name)
            ).to_dict()

        if color_set:
            existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
            if color_set not in existing:
                return error_result(
                    "Color set '{}' not found on '{}'".format(color_set, object_name),
                    "Available color sets: {}".format(existing),
                ).to_dict()
            cmds.polyColorSet(object_name, delete=True, colorSet=color_set)
            removed = [color_set]
        else:
            all_sets = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
            for cs in all_sets:
                cmds.polyColorSet(object_name, delete=True, colorSet=cs)
            removed = list(all_sets)

        return success_result(
            "Removed vertex colors from '{}'".format(object_name),
            object_name=object_name,
            removed_color_sets=removed,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_vertex_colors failed")
        return error_result("Failed to remove vertex colors", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_vertex_colors`."""
    return remove_vertex_colors(**kwargs)


if __name__ == "__main__":
    import json

    result = remove_vertex_colors()
    print(json.dumps(result))
