"""Bake and export the camera for a named shot node."""
from __future__ import annotations

import logging
import os
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Bake the shot's camera and export it as FBX.

    Args:
        params: Dictionary containing:
            - shot (str): Shot node name.  Required.
            - output_path (str): Full output file path (.fbx).  Required.
            - bake (bool): Bake camera animation to world space before export.
                           Default True.

    Returns:
        ActionResultModel with camera name and output path.
    """
    shot = str(params.get("shot", "")).strip()
    output_path = str(params.get("output_path", "")).strip()
    bake = bool(params.get("bake", True))

    if not shot:
        return error_result("Invalid parameters", "'shot' is required.")
    if not output_path:
        return error_result("Invalid parameters", "'output_path' is required.")

    try:
        if not cmds.objExists(shot):
            return error_result("Shot not found", "No node named '{}'.".format(shot))
        if cmds.objectType(shot) != "shot":
            return error_result("Not a shot", "'{}' is not a shot node.".format(shot))

        camera = cmds.getAttr("{}.currentCamera".format(shot))
        if not camera:
            return error_result(
                "No camera assigned",
                "Shot '{}' has no camera assigned.".format(shot),
            )

        start = int(cmds.getAttr("{}.startFrame".format(shot)))
        end = int(cmds.getAttr("{}.endFrame".format(shot)))

        if bake:
            cmds.bakeResults(
                camera,
                simulation=True,
                time=(start, end),
                sampleBy=1,
            )

        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        cmds.select(camera, replace=True)
        cmds.FBXExport("-file", output_path, "-s")

        return success_result(
            "Exported camera '{}' for shot '{}' to '{}'".format(camera, shot, output_path),
            prompt="Use playblast_shot to generate a preview alongside the camera.",
            shot=shot,
            camera=camera,
            output_path=output_path,
            start_frame=start,
            end_frame=end,
        )
    except Exception as exc:
        logger.exception("export_shot_camera failed")
        return error_result("Failed to export camera for shot '{}'".format(shot), str(exc))
