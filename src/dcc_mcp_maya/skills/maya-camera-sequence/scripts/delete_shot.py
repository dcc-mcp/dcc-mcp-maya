"""Delete a shot node from the Camera Sequencer."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Delete a shot node.

    Args:
        params: dict with keys:
            shot (str): Shot node name to delete (required).

    Returns:
        ActionResultModel with deletion status.
    """
    shot = params.get("shot", "")

    if not shot:
        return error_result("Missing parameter", "'shot' is required")

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

        cmds.delete(shot)

        return success_result(
            "Deleted shot '{}'".format(shot),
            prompt="Use list_shots to see remaining shots.",
            deleted=shot,
        )
    except Exception as exc:
        return error_result("Failed to delete shot", str(exc))
