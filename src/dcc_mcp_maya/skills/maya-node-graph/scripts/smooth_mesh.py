"""Apply smooth mesh preview or subdivision to a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def smooth_mesh(
    object_name: str,
    divisions: int = 1,
    method: str = "preview",
) -> dict:
    """Apply smooth mesh preview or subdivision to a polygon mesh.

    Two methods are supported:

    * ``"preview"`` – activates Maya's Smooth Mesh Preview
      (``displaySmoothMesh`` attribute, non-destructive).
    * ``"subdivide"`` – applies ``cmds.polySmooth`` to subdivide the mesh
      destructively.

    Args:
        object_name: Name of the polygon transform/mesh to smooth.
        divisions: Subdivision level.  For ``"preview"`` this sets the
            ``smoothLevel`` attribute.  For ``"subdivide"`` it is the number
            of subdivision iterations.  Default: 1.
        method: ``"preview"`` (default) or ``"subdivide"``.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.divisions``, ``context.method``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_METHODS = ("preview", "subdivide")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if method not in _VALID_METHODS:
            return error_result(
                "Invalid method: {}".format(method),
                "method must be one of {}".format(_VALID_METHODS),
            ).to_dict()

        if divisions < 0:
            return error_result(
                "Invalid divisions: {}".format(divisions),
                "divisions must be >= 0",
            ).to_dict()

        if method == "preview":
            # Enable smooth mesh preview — attribute lives on the shape node
            shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True) or []
            target = shapes[0] if shapes else object_name
            cmds.setAttr("{}.displaySmoothMesh".format(target), 2)  # 2 = smooth + cage
            cmds.setAttr("{}.smoothLevel".format(target), divisions)
            return success_result(
                "Enabled smooth mesh preview on '{}' (level {})".format(object_name, divisions),
                object_name=object_name,
                divisions=divisions,
                method=method,
            ).to_dict()

        # method == "subdivide"
        result = cmds.polySmooth(object_name, divisions=divisions)
        node_name = result[0] if result else "polySmoothFace1"
        return success_result(
            "Subdivided '{}' with {} iteration(s)".format(object_name, divisions),
            object_name=object_name,
            divisions=divisions,
            method=method,
            poly_smooth_node=node_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("smooth_mesh failed")
        return error_result("Failed to smooth mesh {}".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`smooth_mesh`."""
    return smooth_mesh(**kwargs)


if __name__ == "__main__":
    import json

    result = smooth_mesh()
    print(json.dumps(result))
