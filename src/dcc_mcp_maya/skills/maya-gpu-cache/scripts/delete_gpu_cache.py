"""Delete a gpuCache node and optionally its transform from the scene."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Delete a gpuCache node (and optionally its parent transform).

    Args:
        params: Dictionary containing:
            - node (str): Name of the gpuCache node or its parent transform. Required.
            - delete_transform (bool): Also delete the parent transform. Default True.

    Returns:
        ActionResultModel confirming deletion.
    """
    node = str(params.get("node", ""))
    delete_transform = bool(params.get("delete_transform", True))

    if not node:
        return error_result("Invalid parameters", "'node' is required.")
    if not cmds.objExists(node):
        return error_result("Node not found", "Node '{}' does not exist.".format(node))

    try:
        # Resolve to gpuCache shape if transform given
        node_type = cmds.nodeType(node)
        if node_type != "gpuCache":
            shapes = cmds.listRelatives(node, shapes=True, type="gpuCache") or []
            if not shapes:
                return error_result(
                    "Not a GPU cache",
                    "'{}' is not a gpuCache node (type: {}).".format(node, node_type),
                )
            gpu_shape = shapes[0]
            transform = node
        else:
            gpu_shape = node
            parents = cmds.listRelatives(node, parent=True) or []
            transform = parents[0] if parents else None

        deleted = [gpu_shape]
        if delete_transform and transform and cmds.objExists(transform):
            cmds.delete(transform)
            deleted.append(transform)
        else:
            cmds.delete(gpu_shape)

        return success_result(
            "Deleted GPU cache node '{}'".format(gpu_shape),
            prompt="Use list_gpu_caches to verify the node has been removed.",
            deleted_nodes=deleted,
        )
    except Exception as exc:
        return error_result("Failed to delete GPU cache", str(exc))
