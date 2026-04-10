"""List all gpuCache nodes in the Maya scene."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """List all gpuCache nodes currently in the scene.

    Args:
        params: Dictionary (no required keys).

    Returns:
        ActionResultModel with list of gpuCache node info dicts.
    """
    try:
        gpu_nodes: List[str] = cmds.ls(type="gpuCache") or []
        results: List[Dict[str, object]] = []

        for node in gpu_nodes:
            info: Dict[str, object] = {"name": node}

            try:
                info["file_path"] = cmds.getAttr("{}.cacheFileName".format(node))
            except Exception:
                info["file_path"] = None

            try:
                parent = cmds.listRelatives(node, parent=True)
                info["transform"] = parent[0] if parent else None
            except Exception:
                info["transform"] = None

            try:
                info["visible"] = bool(cmds.getAttr("{}.visibility".format(node)))
            except Exception:
                info["visible"] = None

            results.append(info)

        return success_result(
            "Found {} gpuCache node(s)".format(len(results)),
            prompt="Use export_gpu_cache to create new GPU caches or delete_gpu_cache to remove them.",
            gpu_caches=results,
            count=len(results),
        )
    except Exception as exc:
        return error_result("Failed to list GPU caches", str(exc))
