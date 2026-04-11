"""Mirror skin weights across an axis plane."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def mirror_skin_weights(
    mesh: str,
    mirror_mode: str = "YZ",
    surface_association: str = "closestPoint",
    influence_association: str = "closestJoint",
    positive_to_negative: bool = True,
) -> dict:
    """Mirror skin weights across an axis plane.

    Args:
        mesh: Name of the skinned mesh.
        mirror_mode: Mirror plane: ``YZ`` (default, mirrors along X),
            ``XY`` (mirrors along Z), ``XZ`` (mirrors along Y).
        surface_association: Surface point matching method:
            ``closestPoint`` (default), ``rayCast``, ``closestComponent``.
        influence_association: Joint matching method:
            ``closestJoint`` (default), ``closestBone``, ``label``, ``name``.
        positive_to_negative: If True, copy from positive to negative side;
            if False, copy from negative to positive.

    Returns:
        ActionResultModel dict with ``context.skin_cluster_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            ).to_dict()

        sc_list = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster")
        if not sc_list:
            return error_result(
                "No skin cluster on: {}".format(mesh),
                "'{}' has no skinCluster in its history".format(mesh),
            ).to_dict()

        sc = sc_list[0]

        mirror_kwargs = {
            "mirrorMode": mirror_mode,
            "surfaceAssociation": surface_association,
            "influenceAssociation": influence_association,
        }  # type: dict

        if positive_to_negative:
            mirror_kwargs["mirrorInverse"] = False
        else:
            mirror_kwargs["mirrorInverse"] = True

        cmds.copySkinWeights(
            mesh, mirrorMode=mirror_mode, **{k: v for k, v in mirror_kwargs.items() if k != "mirrorMode"}
        )

        return success_result(
            "Mirrored skin weights on '{}' across {} plane".format(mesh, mirror_mode),
            prompt="Check the mirrored side in the component editor to verify weight accuracy.",
            mesh=mesh,
            skin_cluster_name=sc,
            mirror_mode=mirror_mode,
            positive_to_negative=positive_to_negative,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("mirror_skin_weights failed")
        return error_result("Failed to mirror skin weights on '{}'".format(mesh), str(exc)).to_dict()


def main(**kwargs):
    return mirror_skin_weights(**kwargs)


if __name__ == "__main__":
    import json

    result = mirror_skin_weights("pSphere1")
    print(json.dumps(result))
