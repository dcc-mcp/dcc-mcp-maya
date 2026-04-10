"""Generate a playblast preview for a named shot node."""
from __future__ import annotations

import logging
import os
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Render a playblast movie covering the shot's frame range.

    Args:
        params: Dictionary containing:
            - shot (str): Shot node name.  Required.
            - output_path (str): Output file path (without extension).  Required.
            - width (int): Playblast width in pixels.  Default 1280.
            - height (int): Playblast height in pixels.  Default 720.
            - format (str): 'qt' (QuickTime) or 'image'.  Default 'qt'.

    Returns:
        ActionResultModel with output path and frame range.
    """
    shot = str(params.get("shot", "")).strip()
    output_path = str(params.get("output_path", "")).strip()
    width = int(params.get("width", 1280))
    height = int(params.get("height", 720))
    fmt = str(params.get("format", "qt")).lower()

    if not shot:
        return error_result("Invalid parameters", "'shot' is required.")
    if not output_path:
        return error_result("Invalid parameters", "'output_path' is required.")

    try:
        if not cmds.objExists(shot):
            return error_result("Shot not found", "No node named '{}'.".format(shot))
        if cmds.objectType(shot) != "shot":
            return error_result("Not a shot", "'{}' is not a shot node.".format(shot))

        start = int(cmds.getAttr("{}.startFrame".format(shot)))
        end = int(cmds.getAttr("{}.endFrame".format(shot)))

        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        result = cmds.playblast(
            startTime=start,
            endTime=end,
            format=fmt,
            filename=output_path,
            width=width,
            height=height,
            percent=100,
            viewer=False,
            showOrnaments=False,
            forceOverwrite=True,
        )

        return success_result(
            "Playblasted shot '{}' ({}-{}) to '{}'".format(shot, start, end, result),
            prompt="Review the playblast and use export_shot_animation for final export.",
            shot=shot,
            output_path=result,
            start_frame=start,
            end_frame=end,
            width=width,
            height=height,
        )
    except Exception as exc:
        logger.exception("playblast_shot failed")
        return error_result("Failed to playblast shot '{}'".format(shot), str(exc))
