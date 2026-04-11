"""Maya vertex color operation actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional, Tuple

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success


def set_vertex_color(
    object_name: str,
    color: Tuple[float, float, float],
    alpha: float = 1.0,
    vertices: Optional[List[int]] = None,
    color_set: Optional[str] = None,
) -> dict:
    """Set vertex color on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        color: RGB color tuple — each channel in 0.0-1.0 range.
        alpha: Alpha value 0.0-1.0.  Default: 1.0.
        vertices: List of vertex indices to color.  If None, all vertices
            are colored.
        color_set: Target color set name.  If None, uses the current set.

    Returns:
        ActionResultModel dict with ``context.colored_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

        r, g, b = float(color[0]), float(color[1]), float(color[2])
        a = float(alpha)

        kwargs = {
            "rgb": (r, g, b),
            "alpha": a,
            "colorDisplayOption": True,
        }  # type: dict
        if color_set:
            kwargs["colorSet"] = color_set

        if vertices is not None:
            vertex_components = ["{}.vtx[{}]".format(object_name, v) for v in vertices]
            for comp in vertex_components:
                cmds.polyColorPerVertex(comp, **kwargs)
            colored_count = len(vertices)
        else:
            cmds.polyColorPerVertex(object_name, **kwargs)
            total = cmds.polyEvaluate(object_name, vertex=True)
            colored_count = total if isinstance(total, int) else 0

        return skill_success(
            "Set vertex color on '{}' ({} vertices)".format(object_name, colored_count),
            object_name=object_name,
            color=[r, g, b],
            alpha=a,
            colored_count=colored_count,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set vertex color")


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
            return skill_error("Object not found: {}".format(object_name))

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
                return skill_error("Vertex {} not found on '{}'".format(vertex_index, object_name))

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

        return skill_success(
            "Vertex color info for '{}'".format(object_name),
            **result_kwargs,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get vertex color")


def create_color_set(
    object_name: str,
    color_set_name: str,
    representation: str = "RGBA",
) -> dict:
    """Create a new vertex color set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        color_set_name: Name for the new color set.
        representation: Color representation — ``"RGB"`` or ``"RGBA"``.
            Default: ``"RGBA"``.

    Returns:
        ActionResultModel dict.
    """

    valid_reps = ("RGB", "RGBA")
    if representation not in valid_reps:
        return skill_error(
            "Invalid representation: {}".format(representation),
            "Use one of: {}".format(", ".join(valid_reps)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

        existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
        if color_set_name in existing:
            return skill_error("Color set '{}' already exists on '{}'".format(color_set_name, object_name))

        cmds.polyColorSet(
            object_name,
            create=True,
            colorSet=color_set_name,
            representation=representation,
        )

        return skill_success(
            "Created color set '{}' on '{}'".format(color_set_name, object_name),
            object_name=object_name,
            color_set_name=color_set_name,
            representation=representation,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create color set")


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
            return skill_error("Object not found: {}".format(object_name))

        if color_set:
            existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
            if color_set not in existing:
                return skill_error("Color set '{}' not found on '{}'".format(color_set, object_name))
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
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to remove vertex colors")
