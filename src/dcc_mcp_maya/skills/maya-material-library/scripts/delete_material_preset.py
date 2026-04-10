"""Delete a material preset from the library."""
from __future__ import annotations

import os
from typing import Dict

from dcc_mcp_core import error_result, success_result

_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_material_presets")


def run(params: Dict[str, object]):
    """Delete a material preset JSON file from the library.

    Args:
        params: Dictionary with keys:
            - preset_name (str): Name of the preset to delete. Required.
            - preset_dir (str): Directory containing presets. Default ~/.maya_material_presets.

    Returns:
        ActionResultModel with deleted preset path.
    """
    preset_name = params.get("preset_name", "")
    preset_dir = params.get("preset_dir", _PRESET_DIR)

    if not preset_name:
        return error_result("Missing required parameter", "Parameter 'preset_name' is required")

    try:
        preset_path = os.path.join(str(preset_dir), "{}.json".format(preset_name))
        if not os.path.isfile(preset_path):
            return error_result(
                "Preset not found", "No preset file at: {}".format(preset_path)
            )

        os.remove(preset_path)

        return success_result(
            "Deleted material preset '{}'".format(preset_name),
            prompt="Use list_material_presets to see remaining presets.",
            preset_name=preset_name,
            deleted_path=preset_path,
        )
    except Exception as exc:
        return error_result("Failed to delete material preset", str(exc))
