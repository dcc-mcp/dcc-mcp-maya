"""Clean up mesh issues such as non-manifold geometry and lamina faces."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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

        if not cmds.objExists(object_name):
            return maya_error("Object not found: {}".format(object_name), "")

        kwargs = {
            "selectOnly": False,
            "nonManifold": 1 if non_manifold else 0,
            "lamina": 1 if lamina_faces else 0,
            "nsi": 1 if invalid_components else 0,
        }
        cmds.polyClean(object_name, **kwargs)

        return maya_success(
            "Cleaned mesh '{}'".format(object_name),
            object_name=object_name,
            non_manifold=non_manifold,
            lamina_faces=lamina_faces,
            invalid_components=invalid_components,
            prompt="Use get_poly_count or select_by_material to inspect the result.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to clean mesh")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`cleanup_mesh`."""
    return cleanup_mesh(**kwargs)


if __name__ == "__main__":
    import json

    result = cleanup_mesh()
    print(json.dumps(result))
