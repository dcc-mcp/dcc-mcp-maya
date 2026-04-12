"""Apply smooth mesh preview or polygon subdivision to a mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def apply_subdivision(
    mesh: str,
    iterations: int = 1,
    method: str = "preview",
) -> dict:
    """Apply subdivision to a polygon mesh.

    Args:
        mesh: Transform or mesh shape name.
        iterations: Number of subdivision iterations / divisions.  Default: 1.
        method: ``"preview"`` (displaySmoothMesh — non-destructive) or
            ``"subdivide"`` (polySubdivideFacet — destructive).
            Default: ``"preview"``.

    Returns:
        ActionResultModel dict.
    """
    if method not in ("preview", "subdivide"):
        return skill_error(
            "Invalid method: {}".format(method),
            "Use 'preview' or 'subdivide'",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        shapes = cmds.listRelatives(mesh, shapes=True, type="mesh") or []
        if not shapes:
            if cmds.objectType(mesh) == "mesh":
                shapes = [mesh]
            else:
                return skill_error("'{}' has no polygon mesh shape".format(mesh), "")

        shape = shapes[0]

        if method == "preview":
            cmds.setAttr("{}.displaySmoothMesh".format(shape), 2)
            cmds.setAttr("{}.smoothLevel".format(shape), iterations)
        else:
            cmds.polySubdivideFacet(mesh, dv=iterations)

        return skill_success(
            "Subdivision applied to '{}' (method={}, iterations={})".format(mesh, method, iterations),
            mesh=mesh,
            method=method,
            iterations=iterations,
            prompt="Use get_poly_count to verify the increased density.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to apply subdivision")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`apply_subdivision`."""
    return apply_subdivision(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
