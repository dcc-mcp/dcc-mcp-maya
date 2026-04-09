"""Create a passive nRigid collider node on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            ).to_dict()

        mesh_type = cmds.objectType(mesh)
        if mesh_type not in ("transform", "mesh"):
            return error_result(
                "Invalid mesh type: {}".format(mesh_type),
                "'{}' is not a polygon mesh or transform".format(mesh),
            ).to_dict()

        if nucleus and not cmds.objExists(nucleus):
            return error_result(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            ).to_dict()

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
        return success_result(
            "Created nRigid '{}' on mesh '{}'".format(nrigid_node, mesh),
            nrigid_node=nrigid_node,
            mesh=mesh,
            nucleus=used_nucleus,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_nrigid failed")
        return error_result("Failed to create nRigid on '{}'".format(mesh), str(exc)).to_dict()


def main(**kwargs):
    return create_nrigid(**kwargs)


if __name__ == "__main__":
    import json

    result = create_nrigid()
    print(json.dumps(result))
