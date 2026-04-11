"""Clean up mesh issues such as non-manifold geometry and lamina faces."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def cleanup_mesh(
    object_name: str,
    non_manifold: bool = True,
    lamina_faces: bool = True,
    invalid_components: bool = True,
) -> dict:
    """Clean up mesh issues such as non-manifold geometry and lamina faces.

    Args:
        object_name: Transform or mesh name.
        non_manifold: Fix non-manifold geometry.  Default: True.
        lamina_faces: Remove lamina (zero-area) faces.  Default: True.
        invalid_components: Remove invalid (degenerate) polygons.
            Default: True.

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        kwargs = {
            "selectOnly": False,
            "nonManifold": 1 if non_manifold else 0,
            "lamina": 1 if lamina_faces else 0,
            "nsi": 1 if invalid_components else 0,
        }
        cmds.polyClean(object_name, **kwargs)

        return skill_success(
            "Cleaned mesh '{}'".format(object_name),
            object_name=object_name,
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
