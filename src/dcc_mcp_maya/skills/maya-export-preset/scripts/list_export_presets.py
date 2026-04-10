"""List all available export presets in the preset directory."""
from __future__ import annotations

import json
import os
from typing import Dict, List

from dcc_mcp_core import error_result, success_result

_DEFAULT_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_export_presets")


def run(params: Dict[str, object]):
    """List all export presets in the preset directory.

    Args:
        params: Dictionary with keys:
            - preset_dir (str): Directory to scan. Default ~/.maya_export_presets.
            - format_filter (str): Optional format to filter by ('fbx', 'alembic', 'obj').

    Returns:
        ActionResultModel with list of preset summaries.
    """
    preset_dir = params.get("preset_dir", _DEFAULT_PRESET_DIR)
    format_filter = params.get("format_filter", None)

    try:
        if not os.path.isdir(str(preset_dir)):
            return success_result(
                "No export presets found",
                prompt="Use save_export_preset to create a preset.",
                presets=[],
                count=0,
            )

        presets: List[Dict[str, object]] = []
        for fname in sorted(os.listdir(str(preset_dir))):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(str(preset_dir), fname)
            try:
                with open(fpath) as fh:
                    data = json.load(fh)
                if format_filter and data.get("format") != format_filter:
                    continue
                presets.append(
                    {
                        "name": data.get("name", fname[:-5]),
                        "format": data.get("format", "unknown"),
                        "path": fpath,
                    }
                )
            except Exception:
                continue

        return success_result(
            "Found {} export preset(s)".format(len(presets)),
            prompt="Use load_export_preset to view full details of a preset.",
            presets=presets,
            count=len(presets),
        )
    except Exception as exc:
        return error_result("Failed to list export presets", str(exc))
