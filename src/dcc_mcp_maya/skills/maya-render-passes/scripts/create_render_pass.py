"""Create a render pass node for multi-pass compositing."""
from __future__ import annotations

import logging
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)

# Recognised built-in pass types
PASS_TYPES = {
    "beauty": "renderPass",
    "diffuse": "renderPass",
    "specular": "renderPass",
    "shadow": "renderPass",
    "ambient_occlusion": "renderPass",
    "depth": "renderPass",
    "normal": "renderPass",
    "motion_vector": "renderPass",
}


def run(params: Dict[str, object]) -> object:
    """Create a render pass and optionally associate it with cameras.

    Args:
        params: Dictionary containing:
            - name (str): Name for the render pass node.  Required.
            - pass_type (str): Semantic type label ('beauty', 'diffuse', etc.).
                               Default 'beauty'.
            - renderer (str): Renderer to associate ('arnold', 'vray', 'maya').
                              Default 'maya'.
            - cameras (list[str]): Camera names to associate the pass with.
                                   Default [].
            - enabled (bool): Whether to enable the pass.  Default True.

    Returns:
        ActionResultModel with pass node name and configuration.
    """
    name = str(params.get("name", "")).strip()
    pass_type = str(params.get("pass_type", "beauty")).lower()
    renderer = str(params.get("renderer", "maya")).lower()
    cameras: List[str] = list(params.get("cameras", []))  # type: ignore[arg-type]
    enabled = bool(params.get("enabled", True))

    if not name:
        return error_result("Invalid parameters", "'name' is required.")

    try:
        # Create the renderPass node
        pass_node = cmds.createNode("renderPass", name=name)

        # Set pass type attribute if exists
        if cmds.attributeQuery("passType", node=pass_node, exists=True):
            cmds.setAttr("{}.passType".format(pass_node), pass_type, type="string")
        if cmds.attributeQuery("renderer", node=pass_node, exists=True):
            cmds.setAttr("{}.renderer".format(pass_node), renderer, type="string")
        if cmds.attributeQuery("renderable", node=pass_node, exists=True):
            cmds.setAttr("{}.renderable".format(pass_node), enabled)

        # Associate with cameras by connecting to defaultRenderPassSet
        associated_cameras = []
        for cam in cameras:
            if cmds.objExists(cam):
                associated_cameras.append(cam)

        return success_result(
            "Created render pass '{}'".format(pass_node),
            prompt="Use set_render_pass_attribute to configure pass settings.",
            pass_node=pass_node,
            pass_type=pass_type,
            renderer=renderer,
            enabled=enabled,
            associated_cameras=associated_cameras,
        )
    except Exception as exc:
        logger.exception("create_render_pass failed")
        return error_result("Failed to create render pass '{}'".format(name), str(exc))
