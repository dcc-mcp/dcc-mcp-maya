"""List all proxy meshes (lod_level == 0) in the scene."""
from __future__ import annotations

import logging
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Find all transforms tagged with lod_level=0 (proxy) in the scene.

    Args:
        params: Dictionary (no required keys).

    Returns:
        ActionResultModel with list of proxy transform names and their
        corresponding lod_level values.
    """
    try:
        all_transforms = cmds.ls(type="transform") or []
        proxies: List[Dict[str, object]] = []

        for node in all_transforms:
            if not cmds.attributeQuery("lod_level", node=node, exists=True):
                continue
            level = cmds.getAttr("{}.lod_level".format(node))
            visible = cmds.getAttr("{}.visibility".format(node))
            shapes = cmds.listRelatives(node, shapes=True, type="mesh") or []
            poly_count = 0
            if shapes:
                try:
                    poly_count = cmds.polyEvaluate(node, face=True)
                except Exception:
                    pass
            proxies.append(
                {
                    "name": node,
                    "lod_level": int(level),
                    "visible": bool(visible),
                    "poly_count": poly_count,
                }
            )

        return success_result(
            "Found {} LOD-tagged mesh(es)".format(len(proxies)),
            prompt="Use swap_proxy to toggle between proxy and high-res.",
            proxies=proxies,
            count=len(proxies),
        )
    except Exception as exc:
        logger.exception("list_proxies failed")
        return error_result("Failed to list proxies", str(exc))
