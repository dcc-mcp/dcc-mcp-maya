"""Delete a light rig group and all its children."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Delete a light rig group and all lights within it.

    Args:
        params: Dictionary containing:
            - group (str): Name of the light rig group transform.  Required.

    Returns:
        ActionResultModel confirming deletion.
    """
    group = str(params.get("group", "")).strip()

    if not group:
        return error_result("Invalid parameters", "'group' is required.")

    try:
        if not cmds.objExists(group):
            return error_result(
                "Group not found",
                "No node named '{}' exists.".format(group),
            )

        if cmds.nodeType(group) != "transform":
            return error_result(
                "Invalid node type",
                "'{}' is a '{}', not a transform group.".format(group, cmds.nodeType(group)),
            )

        cmds.delete(group)
        return success_result(
            "Deleted light rig group '{}'".format(group),
            prompt="Use create_three_point_rig to create a new lighting rig.",
            deleted=group,
        )
    except Exception as exc:
        logger.exception("delete_light_rig failed")
        return error_result("Failed to delete light rig '{}'".format(group), str(exc))
