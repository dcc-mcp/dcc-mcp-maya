"""Remove skin influences below a threshold and re-normalize."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


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
        cmds.skinPercent(sc, mesh, pruneWeights=prune_value)

        return skill_success(
            "Pruned skin weights on '{}' (threshold={})".format(mesh, prune_value),
            prompt="Run normalize_skin_weights after pruning to ensure weights sum to 1.0.",
            mesh=mesh,
            skin_cluster_name=sc,
            prune_value=prune_value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to prune skin weights on '{}'".format(mesh))


@skill_entry
def main(**kwargs):
    return prune_skin_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
