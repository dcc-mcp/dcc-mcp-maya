"""Copy skin weights from a source mesh to a target mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def copy_skin_weights(
    source_mesh: str,
    target_mesh: str,
    surface_association: str = "closestPoint",
    influence_association: str = "closestJoint",
    normalize: bool = True,
    name: Optional[str] = None,
) -> dict:
    """Copy skin weights from a source mesh to a target mesh.

    Args:
        source_mesh: Name of the source skinned mesh.
        target_mesh: Name of the target mesh to copy weights onto.
        surface_association: Surface point matching method:
            ``closestPoint`` (default), ``rayCast``, ``closestComponent``.
        influence_association: Joint matching method:
            ``closestJoint`` (default), ``closestBone``, ``label``, ``name``.
        normalize: Normalize weights after copy.  Default: True.
        name: Optional name for the skin cluster created on the target.

    Returns:
        ActionResultModel dict with ``context.skin_cluster_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for mesh in (source_mesh, target_mesh):
            if not cmds.objExists(mesh):
                return error_result(
                    "Object not found: {}".format(mesh),
                    "'{}' does not exist in the scene".format(mesh),
                ).to_dict()

        src_clusters = cmds.ls(cmds.listHistory(source_mesh) or [], type="skinCluster")
        if not src_clusters:
            return error_result(
                "No skin cluster on source: {}".format(source_mesh),
                "Source mesh has no skinCluster in its history",
            ).to_dict()

        src_sc = src_clusters[0]
        src_joints = cmds.skinCluster(src_sc, query=True, influence=True) or []

        tgt_clusters = cmds.ls(cmds.listHistory(target_mesh) or [], type="skinCluster")
        if tgt_clusters:
            tgt_sc = tgt_clusters[0]
        else:
            kwargs = {
                "maximumInfluences": 4,
                "bindMethod": 0,
                "toSelectedBones": True,
            }  # type: dict
            if name:
                kwargs["name"] = name
            result = cmds.skinCluster(*(src_joints + [target_mesh]), **kwargs)
            tgt_sc = result[0] if result else (name or "skinCluster1")

        cmds.copySkinWeights(
            sourceSkin=src_sc,
            destinationSkin=tgt_sc,
            noMirror=True,
            surfaceAssociation=surface_association,
            influenceAssociation=influence_association,
            normalize=normalize,
        )

        return success_result(
            "Copied skin weights from '{}' to '{}'".format(source_mesh, target_mesh),
            prompt="Use normalize_skin_weights if blending is needed, or check prune_skin_weights.",
            source_mesh=source_mesh,
            target_mesh=target_mesh,
            skin_cluster_name=tgt_sc,
            joint_count=len(src_joints),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("copy_skin_weights failed")
        return error_result(
            "Failed to copy skin weights from '{}' to '{}'".format(source_mesh, target_mesh),
            str(exc),
        ).to_dict()


def main(**kwargs):
    return copy_skin_weights(**kwargs)


if __name__ == "__main__":
    import json

    result = copy_skin_weights("sourceMesh", "targetMesh")
    print(json.dumps(result))
