"""Delete a proxy mesh node and optionally reveal the high-res source."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Delete a proxy mesh and optionally show its high-res counterpart.

    Args:
        params: Dictionary containing:
            - proxy (str): Name of the proxy mesh transform.  Required.
            - reveal_source (str): Name of the high-res mesh to show after
                                   deletion.  Default '' (no-op).

    Returns:
        ActionResultModel confirming deletion.
    """
    proxy = str(params.get("proxy", "")).strip()
    reveal_source = str(params.get("reveal_source", "")).strip()

    if not proxy:
        return error_result("Invalid parameters", "'proxy' is required.")

    try:
        if not cmds.objExists(proxy):
            return error_result(
                "Proxy not found",
                "No node named '{}' exists.".format(proxy),
            )

        if cmds.nodeType(proxy) != "transform":
            return error_result(
                "Invalid node type",
                "'{}' is a '{}', not a transform.".format(proxy, cmds.nodeType(proxy)),
            )

        cmds.delete(proxy)

        revealed = None
        if reveal_source and cmds.objExists(reveal_source):
            cmds.showHidden(reveal_source)
            revealed = reveal_source

        return success_result(
            "Deleted proxy '{}'".format(proxy),
            prompt="Use create_proxy to create a new proxy if needed.",
            deleted=proxy,
            revealed=revealed,
        )
    except Exception as exc:
        logger.exception("delete_proxy failed")
        return error_result("Failed to delete proxy '{}'".format(proxy), str(exc))
