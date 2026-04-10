"""Associate a render pass with a render layer."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Connect a renderPass node to a renderLayer so it renders for that layer.

    This establishes the message connection between the render pass and the
    render layer's renderPass plug, enabling per-layer pass configuration.

    Args:
        params: Dictionary containing:
            - pass_name (str): Name of the renderPass node.  Required.
            - layer_name (str): Name of the renderLayer node.  Required.

    Returns:
        ActionResultModel confirming the connection.
    """
    pass_name = str(params.get("pass_name", "")).strip()
    layer_name = str(params.get("layer_name", "")).strip()

    if not pass_name:
        return error_result("Invalid parameters", "'pass_name' is required.")
    if not layer_name:
        return error_result("Invalid parameters", "'layer_name' is required.")

    try:
        if not cmds.objExists(pass_name):
            return error_result(
                "Render pass not found",
                "No node named '{}' exists.".format(pass_name),
            )
        if cmds.nodeType(pass_name) != "renderPass":
            return error_result(
                "Invalid node type",
                "'{}' is not a renderPass node.".format(pass_name),
            )
        if not cmds.objExists(layer_name):
            return error_result(
                "Render layer not found",
                "No node named '{}' exists.".format(layer_name),
            )
        if cmds.nodeType(layer_name) != "renderLayer":
            return error_result(
                "Invalid node type",
                "'{}' is not a renderLayer node.".format(layer_name),
            )

        # Connect message attribute of the pass to the layer's renderPass array
        existing = cmds.listConnections(
            "{}.message".format(pass_name),
            destination=True,
            source=False,
            type="renderLayer",
        ) or []
        if layer_name in existing:
            return success_result(
                "Render pass '{}' is already connected to layer '{}'".format(pass_name, layer_name),
                prompt="No action needed; pass is already assigned to this layer.",
                pass_node=pass_name,
                layer_node=layer_name,
                already_connected=True,
            )

        # Find next free index in layer.renderPass[*]
        indices = cmds.getAttr("{}.renderPass".format(layer_name), multiIndices=True) or []
        next_idx = (max(indices) + 1) if indices else 0
        cmds.connectAttr(
            "{}.message".format(pass_name),
            "{}.renderPass[{}]".format(layer_name, next_idx),
        )

        return success_result(
            "Assigned pass '{}' to layer '{}'".format(pass_name, layer_name),
            prompt="Use list_render_passes with a renderer filter to verify assignments.",
            pass_node=pass_name,
            layer_node=layer_name,
            index=next_idx,
        )
    except Exception as exc:
        logger.exception("assign_pass_to_layer failed")
        return error_result(
            "Failed to assign pass '{}' to layer '{}'".format(pass_name, layer_name),
            str(exc),
        )
