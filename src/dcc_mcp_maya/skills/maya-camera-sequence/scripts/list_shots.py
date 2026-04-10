"""List all shot nodes in the Camera Sequencer."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """List all shot nodes in the scene.

    Args:
        params: dict (no required keys).

    Returns:
        ActionResultModel with list of shot info dicts.
    """
    try:
        shot_nodes = cmds.ls(type="shot") or []
        result: List[Dict] = []

        for shot in shot_nodes:
            camera = cmds.shot(shot, query=True, camera=True) or ""
            start_frame = cmds.shot(shot, query=True, startTime=True)
            end_frame = cmds.shot(shot, query=True, endTime=True)
            seq_start = cmds.shot(shot, query=True, sequenceStartTime=True)
            seq_end = cmds.shot(shot, query=True, sequenceEndTime=True)

            result.append(
                {
                    "shot": shot,
                    "camera": camera,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "sequence_start": seq_start,
                    "sequence_end": seq_end,
                    "duration": end_frame - start_frame,
                }
            )

        # Sort by sequence start time
        result.sort(key=lambda x: x["sequence_start"])

        return success_result(
            "Found {} shot(s)".format(len(result)),
            prompt="Use set_shot_camera to reassign cameras, or create_shot to add more shots.",
            shots=result,
            count=len(result),
        )
    except Exception as exc:
        return error_result("Failed to list shots", str(exc))
