"""Toggle visibility between proxy and high-resolution mesh."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Swap visibility between a proxy and its high-res counterpart.

    Both meshes must have the 'lod_level' attribute set (0=proxy, 1=high-res)
    as created by create_proxy.

    Args:
        params: Dictionary containing:
            - proxy (str): Name of the proxy mesh transform.  Required.
            - source (str): Name of the high-res mesh transform.  Required.
            - show_proxy (bool): True to show proxy / hide source.
                                 False to show source / hide proxy.
                                 Default True.

    Returns:
        ActionResultModel confirming the visibility state.
    """
    proxy = str(params.get("proxy", "")).strip()
    source = str(params.get("source", "")).strip()
    show_proxy = bool(params.get("show_proxy", True))

    if not proxy:
        return error_result("Invalid parameters", "'proxy' is required.")
    if not source:
        return error_result("Invalid parameters", "'source' is required.")

    try:
        for node in (proxy, source):
            if not cmds.objExists(node):
                return error_result(
                    "Node not found",
                    "No node named '{}' exists.".format(node),
                )

        if show_proxy:
            cmds.showHidden(proxy)
            cmds.hide(source)
            active, hidden = proxy, source
        else:
            cmds.showHidden(source)
            cmds.hide(proxy)
            active, hidden = source, proxy

        return success_result(
            "Showing '{}', hiding '{}'".format(active, hidden),
            prompt="Use swap_proxy again to toggle back.",
            visible=active,
            hidden=hidden,
            show_proxy=show_proxy,
        )
    except Exception as exc:
        logger.exception("swap_proxy failed")
        return error_result("Failed to swap proxy/source visibility", str(exc))
