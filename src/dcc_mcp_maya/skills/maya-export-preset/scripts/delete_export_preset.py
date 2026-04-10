"""Delete an export preset by name."""
from __future__ import annotations

import os
from typing import Dict

from dcc_mcp_core import error_result, success_result

_DEFAULT_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_export_presets")


def _preset_path(preset_dir: str, name: str) -> str:
    return os.path.join(preset_dir, "{}.json".format(name))


def run(params: Dict[str, object]):
    """Delete an export preset file.

    Args:
        params: Dictionary with keys:
            - name (str): Preset name to delete.
            - preset_dir (str): Directory. Default ~/.maya_export_presets.

    Returns:
        ActionResultModel with deleted path.
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
                "No preset named '{}' in '{}'".format(name, preset_dir),
            )

        os.remove(path)
        return success_result(
            "Deleted export preset '{}'".format(name),
            prompt="Use list_export_presets to see remaining presets.",
            name=name,
            path=path,
        )
    except Exception as exc:
        return error_result("Failed to delete export preset", str(exc))
