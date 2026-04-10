"""Export animation for a named shot node as FBX or Alembic."""
from __future__ import annotations

import logging
import os
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Export animated objects for a shot to FBX or Alembic.

    Args:
        params: Dictionary containing:
            - shot (str): Shot node name.  Required.
            - output_path (str): Full output file path.  Required.
            - format (str): 'fbx' or 'alembic'.  Default 'fbx'.
            - objects (list[str]): Objects to export.  If empty, uses all DAG.

    Returns:
        ActionResultModel with output path and frame range.
    """
    shot = str(params.get("shot", "")).strip()
    output_path = str(params.get("output_path", "")).strip()
    fmt = str(params.get("format", "fbx")).lower()
    objects = params.get("objects", [])

    if not shot:
        return error_result("Invalid parameters", "'shot' is required.")
    if not output_path:
        return error_result("Invalid parameters", "'output_path' is required.")
    if fmt not in ("fbx", "alembic"):
        return error_result(
            "Invalid format",
            "format must be 'fbx' or 'alembic', got '{}'.".format(fmt),
        )

    try:
        if not cmds.objExists(shot):
            return error_result("Shot not found", "No node named '{}'.".format(shot))
        if cmds.objectType(shot) != "shot":
            return error_result("Not a shot", "'{}' is not a shot node.".format(shot))

        start = cmds.getAttr("{}.startFrame".format(shot))
        end = cmds.getAttr("{}.endFrame".format(shot))

        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if objects:
            cmds.select(objects, replace=True)
        else:
            cmds.select(cmds.ls(dag=True, long=True), replace=True)

        if fmt == "fbx":
            cmds.FBXExport("-file", output_path, "-s")
        else:
            cmds.AbcExport(
                "-frameRange {} {} -file {}".format(int(start), int(end), output_path)
            )

        return success_result(
            "Exported shot '{}' ({}-{}) to '{}'".format(shot, int(start), int(end), output_path),
            prompt="Use export_shot_camera to also export the camera track.",
            shot=shot,
            output_path=output_path,
            format=fmt,
            start_frame=start,
            end_frame=end,
        )
    except Exception as exc:
        logger.exception("export_shot_animation failed")
        return error_result("Failed to export shot '{}'".format(shot), str(exc))
