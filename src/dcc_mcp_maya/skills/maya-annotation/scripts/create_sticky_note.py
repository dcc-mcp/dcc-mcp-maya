"""Create a sticky note on a node in the Node Editor / Hypergraph."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Add a sticky note (notes attribute) to a Maya node.

    Args:
        params: Dictionary with keys:
            - node (str): Node to attach the note to.
            - text (str): Note text content.

    Returns:
        ActionResultModel with node name and note text.
    """
    node = params.get("node", "")
    text = params.get("text", "")

    if not node:
        return error_result("Missing required parameter", "Parameter 'node' is required")
    if not text:
        return error_result("Missing required parameter", "Parameter 'text' is required")

    try:
        if not cmds.objExists(str(node)):
            return error_result("Node not found", "Node '{}' does not exist".format(node))

        # Maya stores notes in the 'notes' string attribute
        if not cmds.attributeQuery("notes", node=str(node), exists=True):
            cmds.addAttr(str(node), longName="notes", dataType="string")

        cmds.setAttr("{}.notes".format(node), str(text), type="string")

        return success_result(
            "Sticky note added to '{}'".format(node),
            prompt="Note is visible in the Attribute Editor under Extra Attributes.",
            node=node,
            text=text,
        )
    except Exception as exc:
        return error_result("Failed to create sticky note", str(exc))
