"""Set an attribute on a gpuCache node."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

# Common gpuCache attributes
_GPU_CACHE_ATTRS: List[str] = [
    "cacheFileName",
    "cacheGeomPath",
    "gpuMemoryUsed",
    "visibility",
]


def run(params: Dict[str, object]) -> object:
    """Set an attribute on a gpuCache node.

    Args:
        params: Dictionary containing:
            - node (str): Name of the gpuCache shape node. Required.
            - attribute (str): Attribute name to set. Required.
            - value: New value to set (string, float, bool, or list). Required.

    Returns:
        ActionResultModel confirming the change.
    """
    node = str(params.get("node", ""))
    attribute = str(params.get("attribute", ""))
    value = params.get("value")

    if not node or not attribute:
        return error_result(
            "Invalid parameters",
            "'node' and 'attribute' are required.",
        )
    if value is None:
        return error_result("Invalid parameters", "'value' is required.")
    if not cmds.objExists(node):
        return error_result("Node not found", "Node '{}' does not exist.".format(node))

    full_attr = "{}.{}".format(node, attribute)
    if not cmds.attributeQuery(attribute, node=node, exists=True):
        return error_result(
            "Attribute not found",
            "Attribute '{}' does not exist on '{}'.".format(attribute, node),
        )

    try:
        if isinstance(value, str):
            cmds.setAttr(full_attr, value, type="string")
        elif isinstance(value, (list, tuple)):
            cmds.setAttr(full_attr, *value)
        else:
            cmds.setAttr(full_attr, value)

        return success_result(
            "Set '{}.{}' = {}".format(node, attribute, value),
            prompt="Use list_gpu_caches to see the updated node info.",
            node=node,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return error_result("Failed to set GPU cache attribute", str(exc))
