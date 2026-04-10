"""Create a shot node in the Maya Camera Sequencer."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Create a new shot in the sequencer.

    Args:
        params: dict with keys:
            name (str): Shot name. Default "shot1".
            camera (str): Camera to associate with the shot. Default "persp".
            start_frame (float): Shot start frame. Default 1.
            end_frame (float): Shot end frame. Default 24.
            sequence_start (float): Sequencer start time. Default same as start_frame.

    Returns:
        ActionResultModel with shot node name and frame range.
    """
    name = params.get("name", "shot1")
    camera = params.get("camera", "persp")
    start_frame = float(params.get("start_frame", 1))
    end_frame = float(params.get("end_frame", 24))
    sequence_start = float(params.get("sequence_start", start_frame))

    try:
        # Validate camera exists
        if not cmds.objExists(camera):
            return error_result(
                "Camera not found", "Camera '{}' does not exist".format(camera)
            )

        shot_node = cmds.shot(
            name,
            camera=camera,
            startTime=start_frame,
            endTime=end_frame,
            sequenceStartTime=sequence_start,
            sequenceEndTime=sequence_start + (end_frame - start_frame),
        )

        return success_result(
            "Created shot '{}'".format(shot_node),
            prompt="Use list_shots to see all shots, or set_shot_camera to change the camera.",
            shot=shot_node,
            camera=camera,
            start_frame=start_frame,
            end_frame=end_frame,
            sequence_start=sequence_start,
        )
    except Exception as exc:
        return error_result("Failed to create shot", str(exc))
