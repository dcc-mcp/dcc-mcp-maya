"""Remove vertex colors from a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def remove_vertex_colors(object_name: str, color_set: Optional[str] = None) -> dict:
    """Remove vertex colors from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        color_set: Specific color set to remove.  If None, removes all
            vertex color data from the mesh.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name), "'{}' does not exist".format(object_name)
            )

        if color_set:
            existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
            if color_set not in existing:
                return maya_error(
                    "Color set '{}' not found on '{}'".format(color_set, object_name),
                    "Available color sets: {}".format(existing),
                )
            cmds.polyColorSet(object_name, delete=True, colorSet=color_set)
            removed = [color_set]
        else:
            all_sets = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
            for cs in all_sets:
                cmds.polyColorSet(object_name, delete=True, colorSet=cs)
            removed = list(all_sets)

        return maya_success(
            "Removed vertex colors from '{}'".format(object_name),
            object_name=object_name,
            removed_color_sets=removed,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to remove vertex colors")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_vertex_colors`."""
    return remove_vertex_colors(**kwargs)

if __name__ == "__main__":
    import json

    result = remove_vertex_colors()
    print(json.dumps(result))
