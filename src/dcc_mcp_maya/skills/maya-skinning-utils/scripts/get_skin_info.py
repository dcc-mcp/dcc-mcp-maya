"""Query skin cluster information for a mesh."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Get skinCluster info: influences, vertex count, max influences.

    Args:
        params: dict with keys:
            mesh (str): Mesh name to query (required).

    Returns:
        ActionResultModel with skin cluster details.
    """
    mesh = params.get("mesh", "")

    if not mesh:
        return error_result("Missing parameter", "'mesh' is required")

    try:
        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found", "Node '{}' does not exist".format(mesh)
            )

        skin_clusters = cmds.ls(
            cmds.listHistory(mesh), type="skinCluster"
        )
        if not skin_clusters:
            return error_result(
                "No skinCluster found",
                "Mesh '{}' has no skinCluster deformer".format(mesh),
            )
        skin_cluster = skin_clusters[0]

        # Query influences
        influences = cmds.skinCluster(skin_cluster, query=True, influence=True) or []

        # Max influences per vertex
        max_influences = cmds.skinCluster(
            skin_cluster, query=True, maximumInfluences=True
        )
        normalize_mode = cmds.getAttr("{}.normalizeWeights".format(skin_cluster))
        mode_names = {0: "none", 1: "interactive", 2: "post"}

        influence_info: List[Dict] = []
        for inf in influences:
            influence_info.append(
                {
                    "joint": inf,
                    "type": cmds.nodeType(inf),
                }
            )

        vertex_count = cmds.polyEvaluate(mesh, vertex=True)

        return success_result(
            "SkinCluster '{}': {} influences, {} vertices".format(
                skin_cluster, len(influences), vertex_count
            ),
            prompt="Use prune_skin_weights to reduce influence count, or copy_skin_weights to transfer to another mesh.",
            skin_cluster=skin_cluster,
            mesh=mesh,
            influences=influence_info,
            influence_count=len(influences),
            vertex_count=vertex_count,
            max_influences=max_influences,
            normalize_mode=mode_names.get(normalize_mode, str(normalize_mode)),
        )
    except Exception as exc:
        return error_result("Failed to get skin info", str(exc))
