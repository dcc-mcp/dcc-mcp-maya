"""Load and return an export preset by name."""
from __future__ import annotations

import json
import os
from typing import Dict

from dcc_mcp_core import error_result, success_result

_DEFAULT_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_export_presets")


def _preset_path(preset_dir: str, name: str) -> str:
    return os.path.join(preset_dir, "{}.json".format(name))


def run(params: Dict[str, object]):
    """Load an export preset from disk.

    Args:
        params: Dictionary with keys:
            - name (str): Preset name to load.
            - preset_dir (str): Directory to read from. Default ~/.maya_export_presets.

    Returns:
        ActionResultModel with preset data.
    """
    name = params.get("name", "")
    preset_dir = params.get("preset_dir", _DEFAULT_PRESET_DIR)

    if not name:
        return error_result("Missing required parameter", "Parameter 'name' is required")

    try:
        path = _preset_path(str(preset_dir), str(name))
        if not os.path.isfile(path):
            return error_result(
                "Preset not found",
                "No preset named '{}' found in '{}'".format(name, preset_dir),
            )

        with open(path) as fh:
            preset_data = json.load(fh)

        return success_result(
            "Loaded export preset '{}'".format(name),
            prompt="Use apply_export_preset to apply these settings for export.",
            preset=preset_data,
        )
    except Exception as exc:
        return error_result("Failed to load export preset", str(exc))
