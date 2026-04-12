"""Clean up polygon mesh issues such as non-manifold geometry and lamina faces."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def cleanup_mesh(
    mesh: str,
    non_manifold: bool = True,
    lamina_faces: bool = True,
    invalid_components: bool = True,
) -> dict:
    """Clean up mesh issues such as non-manifold geometry and lamina faces.

    Args:
        mesh: Transform or mesh node name.
        non_manifold: Fix non-manifold geometry.  Default: True.
        lamina_faces: Remove lamina (zero-area) faces.  Default: True.
        invalid_components: Remove invalid (degenerate) polygons.
            Default: True.

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        # polyClean Python flags (long names as of Maya 2022+):
        # nonManifold (-nm), lamina (-lm), cleanVertices (-cv)/cleanEdges (-ce)/cleanFaces (-cf)
        clean_kwargs = {}
        if non_manifold:
            clean_kwargs["nonManifold"] = True
        if lamina_faces:
            clean_kwargs["lamina"] = True
        if invalid_components:
            clean_kwargs["cleanVertices"] = True
            clean_kwargs["cleanEdges"] = True
            clean_kwargs["cleanFaces"] = True
        try:
            if clean_kwargs:
                cmds.polyClean(mesh, **clean_kwargs)
            else:
                cmds.polyClean(mesh)
        except Exception:
            # polyClean may raise when there is nothing to clean — treat as success
            pass

        return skill_success(
            "Cleaned mesh '{}'".format(mesh),
            mesh=mesh,
            non_manifold=non_manifold,
            lamina_faces=lamina_faces,
            invalid_components=invalid_components,
            prompt="Use get_poly_count or select_by_material to inspect the result.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to clean mesh")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`cleanup_mesh`."""
    return cleanup_mesh(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
