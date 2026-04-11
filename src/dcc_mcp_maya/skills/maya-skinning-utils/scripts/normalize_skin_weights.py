"""Normalize skin weights so they sum to 1.0 per vertex."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return maya_error(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            )

        sc_list = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster")
        if not sc_list:
            return maya_error(
                "No skin cluster on: {}".format(mesh),
                "'{}' has no skinCluster in its history".format(mesh),
            )

        sc = sc_list[0]
        cmds.setAttr("{}.normalizeWeights".format(sc), normalize_weights)
        cmds.skinPercent(sc, mesh, normalize=True)

        return maya_success(
            "Normalized skin weights on '{}' (cluster: '{}')".format(mesh, sc),
            prompt="Use prune_skin_weights to remove low-influence joints after normalizing.",
            mesh=mesh,
            skin_cluster_name=sc,
            normalize_weights=normalize_weights,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to normalize skin weights on '{}'".format(mesh))


def main(**kwargs):
    return normalize_skin_weights(**kwargs)


if __name__ == "__main__":
    import json

    result = normalize_skin_weights("pSphere1")
    print(json.dumps(result))
