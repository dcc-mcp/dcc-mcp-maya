"""Set vertex color on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional, Tuple

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
        ToolResult dict with ``context.colored_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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
            prompt="Check the result with list_vertex_color or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set vertex color")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_vertex_color`."""
    return set_vertex_color(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
