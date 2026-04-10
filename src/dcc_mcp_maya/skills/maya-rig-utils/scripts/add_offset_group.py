"""Insert an offset (zero) group above a rig control."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Create an offset/zero group above the specified control transform.

    The group is positioned and oriented to match the control's world
    transform, then the control is reparented under it.

    Args:
        params: Dictionary containing:
            - control (str): Name of the control transform.  Required.
            - suffix (str): Suffix appended to the offset group name.
                            Default '_offset'.

    Returns:
        ActionResultModel with group and control names.
    """
    control = str(params.get("control", "")).strip()
    suffix = str(params.get("suffix", "_offset")).strip() or "_offset"

    if not control:
        return error_result("Invalid parameters", "'control' is required.")

    try:
        if not cmds.objExists(control):
            return error_result("Control not found", "No node named '{}'.".format(control))

        group_name = "{}{}".format(control, suffix)
        parent = cmds.listRelatives(control, parent=True) or []

        # Duplicate the control's transform to get a zero-positioned group
        group = cmds.group(empty=True, name=group_name)
        cmds.delete(cmds.parentConstraint(control, group))

        if parent:
            cmds.parent(group, parent[0])
        cmds.parent(control, group)

        return success_result(
            "Added offset group '{}' above control '{}'".format(group_name, control),
            prompt="Constrain the offset group to a joint to complete the rig setup.",
            group=group_name,
            control=control,
        )
    except Exception as exc:
        logger.exception("add_offset_group failed")
        return error_result(
            "Failed to add offset group for '{}'".format(control), str(exc)
        )
