"""Tag a Maya node with pipeline asset metadata using custom string attributes."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

# Standard pipeline attribute names written to each tagged node
_PIPELINE_ATTRS: List[str] = [
    "pipeline_asset_name",
    "pipeline_asset_type",
    "pipeline_shot",
    "pipeline_step",
    "pipeline_version",
    "pipeline_note",
]


def run(params: Dict[str, object]) -> object:
    """Tag a Maya node with pipeline asset metadata.

    Adds/updates locked string attributes on the target node so downstream
    tools (Shotgrid loader, Ftrack publisher) can identify the asset.

    Args:
        params: Dictionary containing:
            - node (str): Target transform or shape node. Required.
            - asset_name (str): Asset name (e.g. 'hero_char').
            - asset_type (str): Asset type (e.g. 'character', 'prop', 'env').
            - shot (str): Shot name (e.g. 'sh0010').
            - step (str): Pipeline step (e.g. 'rigging', 'lighting').
            - version (str): Version string (e.g. 'v001').
            - note (str): Free-form note.

    Returns:
        ActionResultModel listing written attributes.
    """
    node = str(params.get("node", ""))
    if not node:
        return error_result("Invalid parameters", "'node' is required.")
    if not cmds.objExists(node):
        return error_result("Node not found", "Node '{}' does not exist.".format(node))

    tag_map: Dict[str, str] = {
        "pipeline_asset_name": str(params.get("asset_name", "")),
        "pipeline_asset_type": str(params.get("asset_type", "")),
        "pipeline_shot": str(params.get("shot", "")),
        "pipeline_step": str(params.get("step", "")),
        "pipeline_version": str(params.get("version", "")),
        "pipeline_note": str(params.get("note", "")),
    }

    written: List[str] = []
    try:
        for attr, value in tag_map.items():
            if not value:
                continue
            full_attr = "{}.{}".format(node, attr)
            if not cmds.attributeQuery(attr, node=node, exists=True):
                cmds.addAttr(node, longName=attr, dataType="string")
                cmds.setAttr(full_attr, value, type="string")
            else:
                cmds.setAttr(full_attr, value, type="string")
            written.append(attr)

        return success_result(
            "Tagged node '{}' with {} pipeline attribute(s)".format(node, len(written)),
            prompt="Use get_asset_tags to verify or query the pipeline tags.",
            node=node,
            written_attributes=written,
        )
    except Exception as exc:
        return error_result("Failed to tag asset", str(exc))
