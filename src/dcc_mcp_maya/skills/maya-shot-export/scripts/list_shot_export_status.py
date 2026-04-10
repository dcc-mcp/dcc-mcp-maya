"""List all shots and their export readiness status."""
from __future__ import annotations

import logging
import os
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Return a status summary for every shot node in the scene.

    For each shot, reports the camera assignment, frame range, and
    whether a given export directory contains an existing output file.

    Args:
        params: Dictionary containing:
            - export_dir (str): Directory to check for existing output files.
                                Optional — if omitted, 'exported' key is skipped.

    Returns:
        ActionResultModel with list of shot status dicts.
    """
    export_dir = str(params.get("export_dir", "")).strip()

    try:
        shot_nodes = cmds.ls(type="shot") or []
        if not shot_nodes:
            return success_result(
                "No shot nodes found in scene",
                prompt="Use create_shot to add shots to the scene.",
                shots=[],
                count=0,
            )

        result = []
        for sn in shot_nodes:
            camera = cmds.getAttr("{}.currentCamera".format(sn)) or ""
            start = int(cmds.getAttr("{}.startFrame".format(sn)))
            end = int(cmds.getAttr("{}.endFrame".format(sn)))
            enabled = bool(cmds.getAttr("{}.shotEnabled".format(sn)))

            info = {
                "shot": sn,
                "camera": camera,
                "start_frame": start,
                "end_frame": end,
                "enabled": enabled,
                "frame_count": end - start + 1,
            }

            if export_dir:
                # Check for any file named after the shot
                candidate = os.path.join(export_dir, sn + ".fbx")
                info["exported"] = os.path.exists(candidate)
                info["export_path"] = candidate

            result.append(info)

        exported_count = sum(1 for s in result if s.get("exported", False))
        return success_result(
            "Found {} shots ({} exported)".format(len(result), exported_count),
            prompt="Use export_shot_animation to export pending shots.",
            shots=result,
            count=len(result),
            exported_count=exported_count,
        )
    except Exception as exc:
        logger.exception("list_shot_export_status failed")
        return error_result("Failed to list shot export status", str(exc))
