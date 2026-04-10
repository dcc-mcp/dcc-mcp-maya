"""Normalize skin weights on a skinCluster deformer."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Normalize skin weights so they sum to 1.0 per vertex.

    Args:
        params: dict with keys:
            mesh (str): Mesh or skinCluster node name (required).
            normalize_mode (str): 'interactive' | 'post' | 'none'. Default 'interactive'.

    Returns:
        ActionResultModel with normalization status.
    """
    mesh = params.get("mesh", "")
    normalize_mode = params.get("normalize_mode", "interactive")

    if not mesh:
        return error_result("Missing parameter", "'mesh' is required")

    valid_modes = ("interactive", "post", "none")
    if normalize_mode not in valid_modes:
        return error_result(
            "Invalid normalize_mode",
            "Must be one of: {}".format(", ".join(valid_modes)),
        )

    try:
        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found", "Node '{}' does not exist".format(mesh)
            )

        # Find skinCluster
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

        mode_map = {"interactive": 1, "post": 2, "none": 0}
        cmds.setAttr(
            "{}.normalizeWeights".format(skin_cluster), mode_map[normalize_mode]
        )

        # Force normalize via skinPercent
        cmds.skinPercent(skin_cluster, mesh, normalize=True)

        return success_result(
            "Normalized skin weights on '{}' (mode: {})".format(
                skin_cluster, normalize_mode
            ),
            prompt="Use prune_skin_weights to remove influences below a threshold.",
            skin_cluster=skin_cluster,
            normalize_mode=normalize_mode,
        )
    except Exception as exc:
        return error_result("Failed to normalize skin weights", str(exc))
