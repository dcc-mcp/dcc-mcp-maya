"""Get vertex color information from a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def get_vertex_color(
    object_name: str,
    vertex_index: Optional[int] = None,
    color_set: Optional[str] = None,
) -> dict:
    """Get vertex color information from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        vertex_index: Specific vertex index to query.  If None, returns
            summary info (color set names and count).
        color_set: Color set name to query.  If None, uses the current set.

    Returns:
        ActionResultModel dict with color data.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error("Object not found: {}".format(object_name))

        color_sets = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
        current_set = cmds.polyColorSet(object_name, query=True, currentColorSet=True)
        if isinstance(current_set, list):
            current_set = current_set[0] if current_set else None

        result_kwargs = {
            "color_sets": color_sets,
            "current_color_set": current_set,
        }  # type: dict

        if vertex_index is not None:
            component = "{}.vtx[{}]".format(object_name, vertex_index)
            if not cmds.objExists(component):
                return maya_error("Vertex {} not found on '{}'".format(vertex_index, object_name))

            query_kwargs = {}  # type: dict
            if color_set:
                query_kwargs["colorSet"] = color_set

            rgba = cmds.polyColorPerVertex(component, query=True, rgba=True)
            if rgba and len(rgba) >= 4:
                result_kwargs["vertex_index"] = vertex_index
                result_kwargs["color"] = [rgba[0], rgba[1], rgba[2]]
                result_kwargs["alpha"] = rgba[3]
            else:
                result_kwargs["vertex_index"] = vertex_index
                result_kwargs["color"] = [1.0, 1.0, 1.0]
                result_kwargs["alpha"] = 1.0

        return maya_success("Vertex color info for '{}'".format(object_name), **result_kwargs)
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to get vertex color")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_vertex_color`."""
    return get_vertex_color(**kwargs)

if __name__ == "__main__":
    import json

    result = get_vertex_color()
    print(json.dumps(result))
