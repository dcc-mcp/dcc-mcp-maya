"""Apply smooth mesh preview or subdivision to a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

    _VALID_METHODS = ("preview", "subdivide")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        if method not in _VALID_METHODS:
            return skill_error(
                "Invalid method: {}".format(method),
                "method must be one of {}".format(_VALID_METHODS),
            )

        if divisions < 0:
            return skill_error(
                "Invalid divisions: {}".format(divisions),
                "divisions must be >= 0",
            )

        if method == "preview":
            # Enable smooth mesh preview — attribute lives on the shape node
            shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True) or []
            target = shapes[0] if shapes else object_name
            cmds.setAttr("{}.displaySmoothMesh".format(target), 2)  # 2 = smooth + cage
            cmds.setAttr("{}.smoothLevel".format(target), divisions)
            return skill_success(
                "Enabled smooth mesh preview on '{}' (level {})".format(object_name, divisions),
                object_name=object_name,
                divisions=divisions,
                method=method,
                prompt="Check the result with list_node_graph or use related actions to continue.",
            )

        # method == "subdivide"
        result = cmds.polySmooth(object_name, divisions=divisions)
        node_name = result[0] if result else "polySmoothFace1"
        return skill_success(
            "Subdivided '{}' with {} iteration(s)".format(object_name, divisions),
            object_name=object_name,
            divisions=divisions,
            method=method,
            poly_smooth_node=node_name,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to smooth mesh {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`smooth_mesh`."""
    return smooth_mesh(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
