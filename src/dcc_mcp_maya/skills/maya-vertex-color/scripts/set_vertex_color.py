"""Set vertex color on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

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

        return success_result(
            "Set vertex color on '{}' ({} vertices)".format(object_name, colored_count),
            object_name=object_name,
            color=[r, g, b],
            alpha=a,
            colored_count=colored_count,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_vertex_color failed")
        return error_result("Failed to set vertex color", str(exc)).to_dict()


def main(**kwargs):
    return set_vertex_color(**kwargs)


if __name__ == "__main__":
    import json

    result = set_vertex_color()
    print(json.dumps(result))
