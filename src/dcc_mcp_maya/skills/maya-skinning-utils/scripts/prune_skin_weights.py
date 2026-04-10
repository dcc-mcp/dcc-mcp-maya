"""Remove skin influences below a threshold and re-normalize."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def prune_skin_weights(
    mesh: str,
    prune_value: float = 0.01,
) -> dict:
    """Remove skin cluster influences below a threshold and re-normalize.

    Args:
        mesh: Name of the skinned mesh.
        prune_value: Minimum weight value to keep.  Influences below this
            threshold are zeroed out and remaining weights are re-normalized.
            Default: 0.01.

    Returns:
        ActionResultModel dict with ``context.skin_cluster_name`` and
        ``context.prune_value``.
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
        cmds.skinPercent(sc, mesh, pruneWeights=prune_value)

        return success_result(
            "Pruned skin weights on '{}' (threshold={})".format(mesh, prune_value),
            prompt="Run normalize_skin_weights after pruning to ensure weights sum to 1.0.",
            mesh=mesh,
            skin_cluster_name=sc,
            prune_value=prune_value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("prune_skin_weights failed")
        return error_result("Failed to prune skin weights on '{}'".format(mesh), str(exc)).to_dict()


def main(**kwargs):
    return prune_skin_weights(**kwargs)


if __name__ == "__main__":
    import json

    result = prune_skin_weights("pSphere1")
    print(json.dumps(result))
