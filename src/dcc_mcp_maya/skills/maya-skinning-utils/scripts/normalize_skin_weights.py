"""Normalize skin weights so they sum to 1.0 per vertex."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        sc_list = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster")
        if not sc_list:
            return skill_error(
                "No skin cluster on: {}".format(mesh),
                "'{}' has no skinCluster in its history".format(mesh),
            )

        sc = sc_list[0]
        cmds.setAttr("{}.normalizeWeights".format(sc), normalize_weights)
        cmds.skinPercent(sc, mesh, normalize=True)

        return skill_success(
            "Normalized skin weights on '{}' (cluster: '{}')".format(mesh, sc),
            prompt="Use prune_skin_weights to remove low-influence joints after normalizing.",
            mesh=mesh,
            skin_cluster_name=sc,
            normalize_weights=normalize_weights,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to normalize skin weights on '{}'".format(mesh))


@skill_entry
def main(**kwargs):
    return normalize_skin_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
