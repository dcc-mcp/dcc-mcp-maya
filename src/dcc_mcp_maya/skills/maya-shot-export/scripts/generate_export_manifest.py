"""Generate a JSON export manifest for all shots in the scene."""
from __future__ import annotations

import json
import logging
import os
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Write a JSON manifest listing all shots and their export parameters.

    The manifest is useful for downstream pipeline tools that need to know
    which shots exist and what their frame ranges are.

    Args:
        params: Dictionary containing:
            - output_path (str): Path to write the .json manifest.  Required.
            - project (str): Project name tag written into the manifest.
                             Default ''.
            - export_dir (str): Suggested export directory recorded in manifest.
                                Default ''.

    Returns:
        ActionResultModel with output path and shot count.
    """
    output_path = str(params.get("output_path", "")).strip()
    project = str(params.get("project", "")).strip()
    export_dir = str(params.get("export_dir", "")).strip()

    if not output_path:
        return error_result("Invalid parameters", "'output_path' is required.")

    try:
        shot_nodes = cmds.ls(type="shot") or []
        shots_data = []
        for sn in shot_nodes:
            camera = cmds.getAttr("{}.currentCamera".format(sn)) or ""
            start = int(cmds.getAttr("{}.startFrame".format(sn)))
            end = int(cmds.getAttr("{}.endFrame".format(sn)))
            enabled = bool(cmds.getAttr("{}.shotEnabled".format(sn)))
            shots_data.append({
                "shot": sn,
                "camera": camera,
                "start_frame": start,
                "end_frame": end,
                "enabled": enabled,
            })

        manifest = {
            "project": project,
            "export_dir": export_dir,
            "shot_count": len(shots_data),
            "shots": shots_data,
        }

        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(output_path, "w") as fh:
            json.dump(manifest, fh, indent=2)

        return success_result(
            "Written export manifest with {} shots to '{}'".format(len(shots_data), output_path),
            prompt="Use list_shot_export_status to verify which shots still need exporting.",
            output_path=output_path,
            shot_count=len(shots_data),
            project=project,
        )
    except Exception as exc:
        logger.exception("generate_export_manifest failed")
        return error_result("Failed to generate export manifest", str(exc))
