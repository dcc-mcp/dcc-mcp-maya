"""Query scene-level statistics: polygon counts, node counts and memory."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_scene_statistics(
    include_memory: bool = True,
    node_types: Optional[List[str]] = None,
) -> dict:
    """Return a summary of current scene statistics.

    Args:
        include_memory: Whether to include memory usage. Default True.
        node_types: Specific node types to count additionally. Default ``None``.

    Returns:
        ToolResult dict with keys:
        ``total_nodes``, ``transform_count``, ``mesh_count``,
        ``poly_vertex_count``, ``poly_face_count``, ``scene_file``,
        ``memory_mb`` (optional).
    """

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

        return skill_success(
            "Scene statistics: {} nodes, {} meshes".format(total_nodes, len(meshes)),
            prompt=(
                "Statistics gathered. Large scenes (>500k verts) may be slow to manipulate; "
                "consider using proxy meshes."
            ),
            **ctx,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get scene statistics")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_scene_statistics`."""
    return get_scene_statistics(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
