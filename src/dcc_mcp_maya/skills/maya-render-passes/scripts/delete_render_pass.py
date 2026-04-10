"""Delete a render pass node from the scene."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Delete a renderPass node.

    Args:
        params: Dictionary containing:
            - name (str): Name of the renderPass node to delete.  Required.

    Returns:
        ActionResultModel confirming deletion.
    """
    name = str(params.get("name", "")).strip()

    if not name:
        return error_result("Invalid parameters", "'name' is required.")

    try:
        if not cmds.objExists(name):
            return error_result(
                "Render pass not found",
                "No node named '{}' exists in the scene.".format(name),
            )

        node_type = cmds.nodeType(name)
        if node_type != "renderPass":
            return error_result(
                "Invalid node type",
                "'{}' is a '{}', not a renderPass.".format(name, node_type),
            )

        cmds.delete(name)
        return success_result(
            "Deleted render pass '{}'".format(name),
            prompt="Use create_render_pass to create a new pass.",
            deleted=name,
        )
    except Exception as exc:
        logger.exception("delete_render_pass failed")
        return error_result("Failed to delete render pass '{}'".format(name), str(exc))
