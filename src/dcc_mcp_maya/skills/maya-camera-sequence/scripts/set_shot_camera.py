"""Reassign the camera for an existing shot node."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Change the camera assigned to a shot.

    Args:
        params: dict with keys:
            shot (str): Shot node name (required).
            camera (str): New camera name (required).

    Returns:
        ActionResultModel with updated shot info.
    """
    shot = params.get("shot", "")
    camera = params.get("camera", "")

    if not shot:
        return error_result("Missing parameter", "'shot' is required")
    if not camera:
        return error_result("Missing parameter", "'camera' is required")

    try:
        if not cmds.objExists(shot):
            return error_result(
                "Shot not found", "Shot node '{}' does not exist".format(shot)
            )
        if cmds.nodeType(shot) != "shot":
            return error_result(
                "Invalid node type",
                "'{}' is not a shot node".format(shot),
            )
        if not cmds.objExists(camera):
            return error_result(
                "Camera not found", "Camera '{}' does not exist".format(camera)
            )

        cmds.shot(shot, edit=True, camera=camera)

        return success_result(
            "Shot '{}' camera set to '{}'".format(shot, camera),
            prompt="Use list_shots to verify the assignment.",
            shot=shot,
            camera=camera,
        )
    except Exception as exc:
        return error_result("Failed to set shot camera", str(exc))
