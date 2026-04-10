"""Apply an export preset (load settings and run the export)."""
from __future__ import annotations

import json
import os
from typing import Dict

import maya.cmds as cmds
import maya.mel as mel
from dcc_mcp_core import error_result, success_result

_DEFAULT_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_export_presets")

_FBX_SETTING_MAP = {
    "animation": "FBXExportBakeAnimation",
    "cameras": "FBXExportCameras",
    "lights": "FBXExportLights",
    "skin": "FBXExportSkins",
    "smooth_mesh": "FBXExportSmoothMesh",
}


def _preset_path(preset_dir: str, name: str) -> str:
    return os.path.join(preset_dir, "{}.json".format(name))


def run(params: Dict[str, object]):
    """Apply an export preset and export the current selection.

    Args:
        params: Dictionary with keys:
            - name (str): Preset name to apply.
            - output_path (str): Destination file path (overrides preset setting).
            - preset_dir (str): Directory. Default ~/.maya_export_presets.

    Returns:
        ActionResultModel with export path and format.
    """
    name = params.get("name", "")
    output_path = params.get("output_path", "")
    preset_dir = params.get("preset_dir", _DEFAULT_PRESET_DIR)

    if not name:
        return error_result("Missing required parameter", "Parameter 'name' is required")

    try:
        path = _preset_path(str(preset_dir), str(name))
        if not os.path.isfile(path):
            return error_result(
                "Preset not found",
                "No preset named '{}' in '{}'".format(name, preset_dir),
            )

        with open(path) as fh:
            preset_data = json.load(fh)

        fmt = preset_data.get("format", "fbx")
        settings = preset_data.get("settings", {})

        final_path = str(output_path) if output_path else str(settings.get("output_path", ""))
        if not final_path:
            return error_result(
                "Missing output path",
                "Provide 'output_path' parameter or set it in the preset settings",
            )

        if fmt == "fbx":
            for key, mel_cmd in _FBX_SETTING_MAP.items():
                if key in settings:
                    val = "-v true" if settings[key] else "-v false"
                    mel.eval("{} {};".format(mel_cmd, val))
            mel.eval('FBXExport -f "{}";'.format(final_path.replace("\\", "/")))
        elif fmt == "alembic":
            frame_range = settings.get("frame_range", [1, 1])
            selection = cmds.ls(selection=True)
            roots = " ".join(["-root {}".format(s) for s in selection]) if selection else ""
            mel.eval(
                'AbcExport -j "-frameRange {} {} {} -file \\"{}\\""'.format(
                    frame_range[0], frame_range[1], roots, final_path.replace("\\", "/")
                )
            )
        elif fmt == "obj":
            cmds.file(
                final_path,
                force=True,
                type="OBJexport",
                exportSelected=True,
            )
        else:
            return error_result("Unsupported format", "Format '{}' is not supported".format(fmt))

        return success_result(
            "Export preset '{}' applied; exported to '{}'".format(name, final_path),
            prompt="Export complete. Verify the file at the output path.",
            name=name,
            format=fmt,
            output_path=final_path,
        )
    except Exception as exc:
        return error_result("Failed to apply export preset", str(exc))
