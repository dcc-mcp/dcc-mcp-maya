"""List all material presets in the library."""
from __future__ import annotations

import json
import os
from typing import Dict, List

from dcc_mcp_core import error_result, success_result

_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_material_presets")


def run(params: Dict[str, object]):
    """List all saved material presets with shader type and attribute count.

    Args:
        params: Dictionary with keys:
            - preset_dir (str): Directory to search. Default ~/.maya_material_presets.
            - shader_type (str): Filter by shader type (e.g. 'lambert'). Optional.

    Returns:
        ActionResultModel with list of preset metadata.
    """
    preset_dir = params.get("preset_dir", _PRESET_DIR)
    shader_filter = params.get("shader_type", "")

    try:
        preset_dir = str(preset_dir)
        if not os.path.isdir(preset_dir):
            return success_result(
                "No material presets found (directory does not exist)",
                prompt="Use save_material_preset to create the first preset.",
                presets=[],
                count=0,
            )

        presets: List[Dict[str, object]] = []
        for fname in sorted(os.listdir(preset_dir)):
            if not fname.endswith(".json"):
                continue
            preset_name = fname[:-5]
            fpath = os.path.join(preset_dir, fname)
            try:
                with open(fpath) as fh:
                    data = json.load(fh)
                shader_type = data.get("shader_type", "unknown")
                if shader_filter and shader_type != str(shader_filter):
                    continue
                presets.append({
                    "name": preset_name,
                    "shader_type": shader_type,
                    "attribute_count": len(data.get("attributes", {})),
                    "path": fpath,
                })
            except (json.JSONDecodeError, OSError):
                continue

        return success_result(
            "Found {} material preset(s)".format(len(presets)),
            prompt="Use apply_material_preset to apply a preset to a material node.",
            presets=presets,
            count=len(presets),
        )
    except Exception as exc:
        return error_result("Failed to list material presets", str(exc))
