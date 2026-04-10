"""Import a GPU cache (.abc) file into the Maya scene."""
from __future__ import annotations

import os
from typing import Dict, Optional

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Import a GPU cache file into the Maya scene.

    Args:
        params: Dictionary containing:
            - file_path (str): Path to the .abc GPU cache file. Required.
            - node_name (str): Optional name for the gpuCache node.

    Returns:
        ActionResultModel with imported node name.
    """
    file_path = str(params.get("file_path", ""))
    node_name: Optional[str] = params.get("node_name", None)  # type: ignore[assignment]

    if not file_path:
        return error_result("Invalid parameters", "'file_path' is required.")
    if not os.path.exists(file_path):
        return error_result("File not found", "GPU cache file not found: '{}'".format(file_path))

    try:
        if not cmds.pluginInfo("gpuCache", query=True, loaded=True):
            cmds.loadPlugin("gpuCache")

        transform_name = node_name if node_name else "gpuCacheTransform"
        transform = cmds.createNode("transform", name=transform_name)
        gpu_node = cmds.createNode("gpuCache", name="{}_gpuCacheShape".format(transform_name), parent=transform)
        cmds.setAttr("{}.cacheFileName".format(gpu_node), file_path, type="string")

        return success_result(
            "Imported GPU cache '{}' as '{}'".format(os.path.basename(file_path), transform),
            prompt="The GPU cache node provides fast viewport display. Use list_gpu_caches to see all loaded caches.",
            transform=transform,
            gpu_cache_node=gpu_node,
            file_path=file_path,
        )
    except Exception as exc:
        return error_result("Failed to import GPU cache", str(exc))
