"""Prune small skin weights below a threshold."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Remove skin weight influences below a minimum threshold.

    Args:
        params: dict with keys:
            mesh (str): Mesh or skinCluster node name (required).
            threshold (float): Weights below this value are set to 0. Default 0.001.

    Returns:
        ActionResultModel with prune status.
    """
    mesh = params.get("mesh", "")
    threshold = float(params.get("threshold", 0.001))

    if not mesh:
        return error_result("Missing parameter", "'mesh' is required")
    if threshold < 0.0 or threshold > 1.0:
        return error_result(
            "Invalid threshold",
            "Threshold must be between 0.0 and 1.0, got {}".format(threshold),
        )

    try:
        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found", "Node '{}' does not exist".format(mesh)
            )

        node_type = cmds.nodeType(mesh)
        if node_type == "skinCluster":
            skin_cluster = mesh
        else:
            skin_clusters = cmds.ls(
                cmds.listHistory(mesh), type="skinCluster"
            )
            if not skin_clusters:
                return error_result(
                    "No skinCluster found",
                    "Mesh '{}' has no skinCluster deformer".format(mesh),
                )
            skin_cluster = skin_clusters[0]

        cmds.skinPercent(skin_cluster, mesh, pruneWeights=threshold)

        return success_result(
            "Pruned skin weights on '{}' (threshold={})".format(
                skin_cluster, threshold
            ),
            prompt="Use normalize_skin_weights to redistribute the removed weight.",
            skin_cluster=skin_cluster,
            threshold=threshold,
        )
    except Exception as exc:
        return error_result("Failed to prune skin weights", str(exc))
