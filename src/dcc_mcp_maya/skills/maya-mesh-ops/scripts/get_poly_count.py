"""Query polygon statistics for an object or the entire scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def get_poly_count(object_name: Optional[str] = None) -> dict:
    """Query polygon statistics for an object or the entire scene.

    Args:
        object_name: Transform or mesh shape name.  If None, queries the full
            scene.

    Returns:
        ActionResultModel dict with ``context.faces``, ``context.vertices``,
        ``context.edges``, and ``context.triangles``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if object_name:
            err = validate_node_exists(cmds, object_name)
            if err:
                return err
            targets = [object_name]
        else:
            targets = cmds.ls(type="mesh") or []

        total_faces = 0
        total_verts = 0
        total_edges = 0
        total_tris = 0
        per_object = []

        for target in targets:
            try:
                faces = cmds.polyEvaluate(target, face=True)
                verts = cmds.polyEvaluate(target, vertex=True)
                edges = cmds.polyEvaluate(target, edge=True)
                tris = cmds.polyEvaluate(target, triangle=True)
            except Exception:
                faces = verts = edges = tris = 0

            total_faces += faces if isinstance(faces, int) else 0
            total_verts += verts if isinstance(verts, int) else 0
            total_edges += edges if isinstance(edges, int) else 0
            total_tris += tris if isinstance(tris, int) else 0

            if object_name:
                per_object.append(
                    {
                        "name": target,
                        "faces": faces,
                        "vertices": verts,
                        "edges": edges,
                        "triangles": tris,
                    }
                )

        label = "Poly count for '{}'".format(object_name) if object_name else "Scene poly count"
        result_kwargs = {
            "faces": total_faces,
            "vertices": total_verts,
            "edges": total_edges,
            "triangles": total_tris,
        }
        if object_name:
            result_kwargs["objects"] = per_object

        return skill_success(
            label, **result_kwargs, prompt="Use apply_subdivision or cleanup_mesh to adjust the geometry."
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get poly count")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_poly_count`."""
    return get_poly_count(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
