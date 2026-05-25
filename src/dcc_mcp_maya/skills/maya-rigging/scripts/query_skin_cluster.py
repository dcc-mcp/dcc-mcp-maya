"""Query skin-cluster state for a mesh or skinCluster node."""

from __future__ import annotations

from typing import Any, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, validate_node_exists


def _skin_cluster_for_node(cmds: Any, node: str) -> Optional[str]:
    try:
        if cmds.nodeType(node) == "skinCluster":
            return node
    except Exception:  # noqa: BLE001
        pass
    history = cmds.listHistory(node) or []
    clusters = cmds.ls(history, type="skinCluster") or []
    return str(clusters[0]) if clusters else None


def _attr_or_none(cmds: Any, plug: str) -> Any:
    try:
        return cmds.getAttr(plug)
    except Exception:  # noqa: BLE001
        return None


def query_skin_cluster(node: str) -> dict:
    """Return the skinCluster, influences, geometry, and common settings for *node*."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node)
        if err:
            return err

        skin_cluster = _skin_cluster_for_node(cmds, node)
        if not skin_cluster:
            return maya_error(
                "No skinCluster found",
                "The requested node is not a skinCluster and has no skinCluster in its history.",
                node=node,
            )

        influences = cmds.skinCluster(skin_cluster, query=True, influence=True) or []
        geometry = cmds.skinCluster(skin_cluster, query=True, geometry=True) or []
        return maya_success(
            "Queried skinCluster: {}".format(skin_cluster),
            node=node,
            skin_cluster=skin_cluster,
            influences=[str(item) for item in influences],
            influence_count=len(influences),
            geometry=[str(item) for item in geometry],
            max_influences=_attr_or_none(cmds, "{}.maxInfluences".format(skin_cluster)),
            normalize_weights=_attr_or_none(cmds, "{}.normalizeWeights".format(skin_cluster)),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to query skinCluster")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`query_skin_cluster`."""
    return query_skin_cluster(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
