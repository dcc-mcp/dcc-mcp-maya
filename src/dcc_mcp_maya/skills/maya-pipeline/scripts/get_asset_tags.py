"""Read pipeline asset tags from a Maya node's custom string attributes."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

_PIPELINE_ATTRS: List[str] = [
    "pipeline_asset_name",
    "pipeline_asset_type",
    "pipeline_shot",
    "pipeline_step",
    "pipeline_version",
    "pipeline_note",
]


def run(params: Dict[str, object]) -> object:
    """Read pipeline asset tags from a tagged node.

    Args:
        params: Dictionary containing:
            - node (str): Target node to read tags from. Required.

    Returns:
        ActionResultModel with pipeline tag dict.
    """
    node = str(params.get("node", ""))
    if not node:
        return error_result("Invalid parameters", "'node' is required.")
    if not cmds.objExists(node):
        return error_result("Node not found", "Node '{}' does not exist.".format(node))

    try:
        tags: Dict[str, str] = {}
        for attr in _PIPELINE_ATTRS:
            if cmds.attributeQuery(attr, node=node, exists=True):
                val = cmds.getAttr("{}.{}".format(node, attr))
                tags[attr] = val if val else ""

        return success_result(
            "Read {} pipeline tag(s) from '{}'".format(len(tags), node),
            prompt="Use tag_asset to add or update pipeline tags.",
            node=node,
            tags=tags,
        )
    except Exception as exc:
        return error_result("Failed to get asset tags", str(exc))
