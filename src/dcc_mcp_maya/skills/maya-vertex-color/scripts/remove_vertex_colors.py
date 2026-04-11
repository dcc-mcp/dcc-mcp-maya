"""Remove vertex colors from a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        if color_set:
            existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
            if color_set not in existing:
                return skill_error(
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

        return skill_success(
            "Removed vertex colors from '{}'".format(object_name),
            object_name=object_name,
            removed_color_sets=removed,
            prompt="Check the result with list_vertex_color or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to remove vertex colors")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_vertex_colors`."""
    return remove_vertex_colors(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
