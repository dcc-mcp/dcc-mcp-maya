"""Create an nCloth dynamic cloth node on a polygon mesh."""

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
        return success_result(
            "Created nCloth '{}' on mesh '{}'".format(ncloth_node, mesh),
            ncloth_node=ncloth_node,
            mesh=mesh,
            nucleus=used_nucleus,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_ncloth failed")
        return error_result("Failed to create nCloth on '{}'".format(mesh), str(exc)).to_dict()


def main(**kwargs):
    return create_ncloth(**kwargs)


if __name__ == "__main__":
    import json

    result = create_ncloth()
    print(json.dumps(result))
