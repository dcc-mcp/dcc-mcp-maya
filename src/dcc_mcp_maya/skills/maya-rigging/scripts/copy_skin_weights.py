"""Copy or mirror skin weights between skinned meshes."""

from __future__ import annotations

from typing import Any, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success


def _skin_cluster_for_node(cmds: Any, node: str) -> Optional[str]:
    try:
        if cmds.nodeType(node) == "skinCluster":
            return node
    except Exception:  # noqa: BLE001
        pass
    history = cmds.listHistory(node) or []
    clusters = cmds.ls(history, type="skinCluster") or []
    return str(clusters[0]) if clusters else None


def _ensure_target_skin_cluster(
    cmds: Any,
    source_skin_cluster: str,
    target_mesh: str,
    target_skin_cluster: Optional[str],
    create_missing: bool,
) -> Optional[str]:
    if target_skin_cluster:
        return target_skin_cluster
    existing = _skin_cluster_for_node(cmds, target_mesh)
    if existing:
        return existing
    if not create_missing:
        return None
    influences = cmds.skinCluster(source_skin_cluster, query=True, influence=True) or []
    if not influences:
        return None
    result = cmds.skinCluster(*list(influences), target_mesh, toSelectedBones=True)
    return str(result[0]) if result else None


def copy_skin_weights(
    source_mesh: str,
    target_mesh: str,
    source_skin_cluster: Optional[str] = None,
    target_skin_cluster: Optional[str] = None,
    create_missing_target_skin_cluster: bool = False,
    surface_association: str = "closestPoint",
    influence_association: Optional[List[str]] = None,
    mirror: bool = False,
    mirror_mode: str = "YZ",
    normalize: bool = True,
) -> dict:
    """Copy or mirror skin weights between skinned meshes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, [source_mesh, target_mesh])
        if err:
            return err

        source_skin = source_skin_cluster or _skin_cluster_for_node(cmds, source_mesh)
        if not source_skin:
            return maya_error("Source skinCluster not found", "source_mesh has no skinCluster in its history.")

        target_skin = _ensure_target_skin_cluster(
            cmds,
            source_skin,
            target_mesh,
            target_skin_cluster,
            create_missing_target_skin_cluster,
        )
        if not target_skin:
            return maya_error(
                "Target skinCluster not found",
                "target_mesh has no skinCluster; pass create_missing_target_skin_cluster=true to bind it first.",
            )

        associations = influence_association or ["closestJoint", "oneToOne", "name"]
        cmds.copySkinWeights(
            sourceSkin=source_skin,
            destinationSkin=target_skin,
            noMirror=not bool(mirror),
            mirrorMode=str(mirror_mode),
            surfaceAssociation=str(surface_association),
            influenceAssociation=associations,
        )
        if normalize:
            cmds.skinCluster(target_skin, edit=True, forceNormalizeWeights=True)

        return maya_success(
            "Copied skin weights from {} to {}".format(source_mesh, target_mesh),
            source_mesh=source_mesh,
            target_mesh=target_mesh,
            source_skin_cluster=source_skin,
            target_skin_cluster=target_skin,
            mirror=bool(mirror),
            mirror_mode=str(mirror_mode),
            surface_association=str(surface_association),
            influence_association=associations,
            normalized=bool(normalize),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to copy skin weights")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`copy_skin_weights`."""
    return copy_skin_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
