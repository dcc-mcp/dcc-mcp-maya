"""Adjust the start/end frame range of an existing shot node."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Set the frame range for a shot node.

    Args:
        params: dict with keys:
            shot (str): Shot node name (required).
            start_frame (float): New start frame (optional).
            end_frame (float): New end frame (optional).
            sequence_start (float): Sequencer start time (optional).

    Returns:
        ActionResultModel with updated range info.
    """
    shot = params.get("shot", "")
    start_frame = params.get("start_frame")
    end_frame = params.get("end_frame")
    sequence_start = params.get("sequence_start")

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

        if start_frame is not None:
            cmds.shot(shot, edit=True, startTime=float(start_frame))
        if end_frame is not None:
            cmds.shot(shot, edit=True, endTime=float(end_frame))
        if sequence_start is not None:
            cmds.shot(shot, edit=True, sequenceStartTime=float(sequence_start))

        # Read back updated values
        updated_start = cmds.shot(shot, query=True, startTime=True)
        updated_end = cmds.shot(shot, query=True, endTime=True)
        updated_seq = cmds.shot(shot, query=True, sequenceStartTime=True)

        return success_result(
            "Updated shot '{}' range: {}-{} (seq start: {})".format(
                shot, updated_start, updated_end, updated_seq
            ),
            prompt="Use list_shots to verify all shot timings.",
            shot=shot,
            start_frame=updated_start,
            end_frame=updated_end,
            sequence_start=updated_seq,
        )
    except Exception as exc:
        return error_result("Failed to set shot range", str(exc))
