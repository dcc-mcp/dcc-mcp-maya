"""Copy skin weights from a source mesh to a target mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, [source_mesh, target_mesh])
        if err:
            return err

        src_clusters = cmds.ls(cmds.listHistory(source_mesh) or [], type="skinCluster")
        if not src_clusters:
            return skill_error(
                "No skin cluster on source: {}".format(source_mesh),
                "Source mesh has no skinCluster in its history",
            )

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

        return skill_success(
            "Copied skin weights from '{}' to '{}'".format(source_mesh, target_mesh),
            prompt="Use normalize_skin_weights if blending is needed, or check prune_skin_weights.",
            source_mesh=source_mesh,
            target_mesh=target_mesh,
            skin_cluster_name=tgt_sc,
            joint_count=len(src_joints),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_error(
            "Failed to copy skin weights from '{}' to '{}'".format(source_mesh, target_mesh),
            str(exc),
        )


@skill_entry
def main(**kwargs):
    return copy_skin_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
