"""Set per-vertex weights on a cluster deformer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_cluster_weights(
    cluster_node: str,
    mesh: str,
    weights: List[float],
    vertex_indices: Optional[List[int]] = None,
    normalize: bool = True,
) -> dict:
    """Set per-vertex weights on a cluster deformer.

    Args:
        cluster_node: Name of the cluster deformer node (not the handle).
        mesh: Name of the mesh whose vertex weights to set.
        weights: Weight values, one per vertex in *vertex_indices* (or per
            all vertices if *vertex_indices* is ``None``).
        vertex_indices: Specific vertex indices to update.  If ``None``,
            *weights* must cover all vertices in order.
        normalize: When ``True``, clamp weights to ``[0, 1]`` before setting.

    Returns:
        ActionResultModel dict with ``context.vertex_count``.
    """
    if not weights:
        return skill_error(
            "No weights provided",
            "Supply at least one weight value",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, cluster_node)
        if err:
            return err
        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        vertex_count = cmds.polyEvaluate(mesh, vertex=True)

        if vertex_indices is None:
            if len(weights) != vertex_count:
                return skill_error(
                    "Weight count mismatch",
                    "Expected {} weights, got {}".format(vertex_count, len(weights)),
                )
            vertex_indices = list(range(vertex_count))

        if normalize:
            weights = [max(0.0, min(1.0, float(w))) for w in weights]

        for idx, w in zip(vertex_indices, weights):
            vtx = "{}.vtx[{}]".format(mesh, idx)
            cmds.percent(cluster_node, vtx, value=w)

        return skill_success(
            "Set cluster weights on {} vertices of '{}'".format(len(vertex_indices), mesh),
            cluster_node=cluster_node,
            mesh=mesh,
            vertex_count=len(vertex_indices),
            normalize=normalize,
            prompt="Check the result with list_deformers or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set cluster weights")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_cluster_weights`."""
    return set_cluster_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
