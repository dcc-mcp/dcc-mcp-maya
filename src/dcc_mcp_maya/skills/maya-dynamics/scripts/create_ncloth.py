"""Create an nCloth dynamic cloth node on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def create_ncloth(
    mesh: str,
    nucleus: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Create an nCloth dynamic cloth node on a polygon mesh.

    The mesh is converted to nCloth by calling ``cmds.nCloth`` on it.
    The nCloth node is optionally connected to a specific nucleus solver;
    otherwise Maya uses the default nucleus in the scene (or creates one).

    Args:
        mesh: Name of the polygon mesh transform to make into nCloth.
        nucleus: Optional name of an existing nucleus solver to connect the
            nCloth node to.  If ``None``, Maya's default nucleus is used.
        name: Optional name for the nCloth shape node.

    Returns:
        ActionResultModel dict with ``context.ncloth_node``,
        ``context.mesh``, ``context.nucleus``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        mesh_type = cmds.objectType(mesh)
        if mesh_type not in ("transform", "mesh"):
            return skill_error(
                "Invalid mesh type: {}".format(mesh_type),
                "'{}' is not a polygon mesh or transform".format(mesh),
            )

        if nucleus and not cmds.objExists(nucleus):
            return skill_error(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            )

        # Select the mesh and create nCloth
        cmds.select(mesh, replace=True)
        ncloth_kwargs = {}
        if name:
            ncloth_kwargs["name"] = name
        result = cmds.nCloth(**ncloth_kwargs)
        ncloth_node = result[0] if isinstance(result, (list, tuple)) else result

        # Connect to specific nucleus if requested
        if nucleus:
            cmds.connectAttr(
                "{}.startFrame".format(nucleus),
                "{}.startFrame".format(ncloth_node),
                force=True,
            )

        used_nucleus = nucleus or "default"
        return skill_success(
            "Created nCloth '{}' on mesh '{}'".format(ncloth_node, mesh),
            ncloth_node=ncloth_node,
            mesh=mesh,
            nucleus=used_nucleus,
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create nCloth on '{}'".format(mesh))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_ncloth`."""
    return create_ncloth(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
