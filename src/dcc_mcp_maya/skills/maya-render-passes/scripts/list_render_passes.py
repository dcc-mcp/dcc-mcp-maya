"""List all render pass nodes in the current scene."""
from __future__ import annotations

import logging
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """List all renderPass nodes with their attributes.

    Args:
        params: Dictionary containing:
            - renderer (str): Filter by renderer name.  Default '' (all).
            - enabled_only (bool): Only return enabled passes.  Default False.

    Returns:
        ActionResultModel with passes list and count.
    """
    renderer_filter = str(params.get("renderer", "")).lower()
    enabled_only = bool(params.get("enabled_only", False))

    try:
        pass_nodes = cmds.ls(type="renderPass") or []
        passes: List[Dict[str, object]] = []

        for node in pass_nodes:
            pass_type = ""
            if cmds.attributeQuery("passType", node=node, exists=True):
                pass_type = cmds.getAttr("{}.passType".format(node)) or ""
            renderer = ""
            if cmds.attributeQuery("renderer", node=node, exists=True):
                renderer = cmds.getAttr("{}.renderer".format(node)) or ""
            renderable = True
            if cmds.attributeQuery("renderable", node=node, exists=True):
                renderable = bool(cmds.getAttr("{}.renderable".format(node)))

            if renderer_filter and renderer.lower() != renderer_filter:
                continue
            if enabled_only and not renderable:
                continue

            passes.append(
                {
                    "name": node,
                    "pass_type": pass_type,
                    "renderer": renderer,
                    "enabled": renderable,
                }
            )

        return success_result(
            "Found {} render pass(es)".format(len(passes)),
            prompt="Use set_render_pass_attribute to modify pass settings.",
            passes=passes,
            count=len(passes),
        )
    except Exception as exc:
        logger.exception("list_render_passes failed")
        return error_result("Failed to list render passes", str(exc))
