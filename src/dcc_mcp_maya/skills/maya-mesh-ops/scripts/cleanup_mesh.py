"""Clean up mesh issues such as non-manifold geometry and lamina faces."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        kwargs = {
            "selectOnly": False,
            "nonManifold": 1 if non_manifold else 0,
            "lamina": 1 if lamina_faces else 0,
            "nsi": 1 if invalid_components else 0,
        }
        cmds.polyClean(object_name, **kwargs)

        return success_result(
            "Cleaned mesh '{}'".format(object_name),
            object_name=object_name,
            non_manifold=non_manifold,
            lamina_faces=lamina_faces,
            invalid_components=invalid_components,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("cleanup_mesh failed")
        return error_result("Failed to clean mesh", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`cleanup_mesh`."""
    return cleanup_mesh(**kwargs)


if __name__ == "__main__":
    import json

    result = cleanup_mesh()
    print(json.dumps(result))
