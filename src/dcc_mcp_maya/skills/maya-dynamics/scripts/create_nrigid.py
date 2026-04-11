"""Create a passive nRigid collider node on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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


def create_nrigid(
    mesh: str,
    nucleus: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Create a passive nRigid collider node on a polygon mesh.

    The mesh is converted to a passive nRigid collider by calling
    ``cmds.nRigid`` on it.  This allows nCloth and nParticle simulations to
    collide with the mesh.

    Args:
        mesh: Name of the polygon mesh transform to use as a collider.
        nucleus: Optional name of an existing nucleus solver to connect the
            nRigid node to.  If ``None``, Maya's default nucleus is used.
        name: Optional name for the nRigid shape node.

    Returns:
        ActionResultModel dict with ``context.nrigid_node``,
        ``context.mesh``, ``context.nucleus``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return maya_error(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            )

        mesh_type = cmds.objectType(mesh)
        if mesh_type not in ("transform", "mesh"):
            return maya_error(
                "Invalid mesh type: {}".format(mesh_type),
                "'{}' is not a polygon mesh or transform".format(mesh),
            )

        if nucleus and not cmds.objExists(nucleus):
            return maya_error(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            )

        cmds.select(mesh, replace=True)
        nrigid_kwargs = {}
        if name:
            nrigid_kwargs["name"] = name
        result = cmds.nRigid(**nrigid_kwargs)
        nrigid_node = result[0] if isinstance(result, (list, tuple)) else result

        if nucleus:
            cmds.connectAttr(
                "{}.startFrame".format(nucleus),
                "{}.startFrame".format(nrigid_node),
                force=True,
            )

        used_nucleus = nucleus or "default"
        return maya_success(
            "Created nRigid '{}' on mesh '{}'".format(nrigid_node, mesh),
            nrigid_node=nrigid_node,
            mesh=mesh,
            nucleus=used_nucleus,
            prompt="Use list_ncloth_objects to verify or set_ncloth_attribute to tune.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create nRigid on '{}'".format(mesh))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_nrigid`."""
    return create_nrigid(**kwargs)


if __name__ == "__main__":
    import json

    result = create_nrigid()
    print(json.dumps(result))
