"""Snap one object to the position/orientation of another."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Snap source object to the world-space transform of a target object.

    Args:
        params: Dictionary with keys:
            - source (str): Object to move.
            - target (str): Reference object to snap to.
            - snap_translate (bool): Match translation. Default True.
            - snap_rotate (bool): Match rotation. Default True.

    Returns:
        ActionResultModel with resulting transform values.
    """
    source = params.get("source", "")
    target = params.get("target", "")
    snap_translate = params.get("snap_translate", True)
    snap_rotate = params.get("snap_rotate", True)

    if not source:
        return error_result("Missing required parameter", "Parameter 'source' is required")
    if not target:
        return error_result("Missing required parameter", "Parameter 'target' is required")

    try:
        if not cmds.objExists(source):
            return error_result("Object not found", "Source '{}' does not exist".format(source))
        if not cmds.objExists(target):
            return error_result("Object not found", "Target '{}' does not exist".format(target))

        if snap_translate:
            world_pos = cmds.xform(target, query=True, worldSpace=True, translation=True)
            cmds.xform(source, worldSpace=True, translation=world_pos)

        if snap_rotate:
            world_rot = cmds.xform(target, query=True, worldSpace=True, rotation=True)
            cmds.xform(source, worldSpace=True, rotation=world_rot)

        final_t = cmds.xform(source, query=True, worldSpace=True, translation=True)
        final_r = cmds.xform(source, query=True, worldSpace=True, rotation=True)

        return success_result(
            "Snapped '{}' to '{}'".format(source, target),
            prompt="Object has been repositioned. Use set_transform for further adjustments.",
            source=source,
            target=target,
            translate=list(final_t),
            rotate=list(final_r),
        )
    except Exception as exc:
        return error_result("Failed to snap object", str(exc))
