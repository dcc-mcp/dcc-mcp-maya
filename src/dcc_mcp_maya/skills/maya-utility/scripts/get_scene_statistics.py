"""Query scene-level statistics: polygon counts, node counts and memory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_scene_statistics(
    include_memory: bool = True,
    node_types: Optional[List[str]] = None,
) -> dict:
    """Return a summary of current scene statistics.

    Args:
        include_memory: Whether to include memory usage. Default True.
        node_types: Specific node types to count additionally. Default ``None``.

    Returns:
        ActionResultModel dict with keys:
        ``total_nodes``, ``transform_count``, ``mesh_count``,
        ``poly_vertex_count``, ``poly_face_count``, ``scene_file``,
        ``memory_mb`` (optional).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    extra_types = node_types or []

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        total_nodes = len(cmds.ls())
        transforms = cmds.ls(type="transform") or []
        meshes = cmds.ls(type="mesh") or []

        vert_count = 0
        face_count = 0
        for mesh in meshes:
            try:
                vert_count += cmds.polyEvaluate(mesh, vertex=True) or 0
                face_count += cmds.polyEvaluate(mesh, face=True) or 0
            except Exception:
                pass

        # Current scene file path
        try:
            scene_file = cmds.file(query=True, sceneName=True) or ""
        except Exception:
            scene_file = ""

        ctx = {
            "total_nodes": total_nodes,
            "transform_count": len(transforms),
            "mesh_count": len(meshes),
            "poly_vertex_count": vert_count,
            "poly_face_count": face_count,
            "scene_file": scene_file,
        }

        if include_memory:
            try:
                mem_kb = cmds.memory(heapSize=True)
                ctx["memory_mb"] = round(mem_kb / 1024.0, 2)
            except Exception:
                ctx["memory_mb"] = None

        for nt in extra_types:
            key = "{}_count".format(nt)
            ctx[key] = len(cmds.ls(type=nt) or [])

        return success_result(
            "Scene statistics: {} nodes, {} meshes".format(total_nodes, len(meshes)),
            prompt=(
                "Statistics gathered. Large scenes (>500k verts) may be slow to manipulate; "
                "consider using proxy meshes."
            ),
            **ctx,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_scene_statistics failed")
        return error_result("Failed to get scene statistics", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_scene_statistics`."""
    return get_scene_statistics(**kwargs)


if __name__ == "__main__":
    import json

    result = get_scene_statistics()
    print(json.dumps(result))
