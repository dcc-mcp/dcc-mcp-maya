"""Normalize skin weights so they sum to 1.0 per vertex."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def normalize_skin_weights(
    mesh: str,
    normalize_weights: int = 1,
) -> dict:
    """Normalize skin weights so they sum to 1.0 per vertex.

    Args:
        mesh: Name of the skinned mesh.
        normalize_weights: Normalization mode:
            ``0`` = none, ``1`` = interactive (default), ``2`` = post.

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
        cmds.setAttr("{}.normalizeWeights".format(sc), normalize_weights)
        cmds.skinPercent(sc, mesh, normalize=True)

        return success_result(
            "Normalized skin weights on '{}' (cluster: '{}')".format(mesh, sc),
            prompt="Use prune_skin_weights to remove low-influence joints after normalizing.",
            mesh=mesh,
            skin_cluster_name=sc,
            normalize_weights=normalize_weights,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("normalize_skin_weights failed")
        return error_result("Failed to normalize skin weights on '{}'".format(mesh), str(exc)).to_dict()


def main(**kwargs):
    return normalize_skin_weights(**kwargs)


if __name__ == "__main__":
    import json

    result = normalize_skin_weights("pSphere1")
    print(json.dumps(result))
