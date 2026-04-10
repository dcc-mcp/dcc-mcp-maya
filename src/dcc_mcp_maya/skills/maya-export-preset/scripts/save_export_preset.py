"""Save current export settings as a named preset to a JSON file."""
from __future__ import annotations

import json
import os
from typing import Dict

from dcc_mcp_core import error_result, success_result

_DEFAULT_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_export_presets")


def _preset_path(preset_dir: str, name: str) -> str:
    return os.path.join(preset_dir, "{}.json".format(name))


def run(params: Dict[str, object]):
    """Save an export preset to disk.

    Args:
        params: Dictionary with keys:
            - name (str): Preset name (used as filename).
            - format (str): Export format: 'fbx', 'alembic', 'obj'. Default 'fbx'.
            - settings (dict): Key-value pairs to store in the preset.
            - preset_dir (str): Directory to save presets. Default ~/.maya_export_presets.

    Returns:
        ActionResultModel with preset file path.
    """
    name = params.get("name", "")
    fmt = params.get("format", "fbx")
    settings = params.get("settings", {})
    preset_dir = params.get("preset_dir", _DEFAULT_PRESET_DIR)

    if not name:
        return error_result("Missing required parameter", "Parameter 'name' is required")

    try:
        os.makedirs(preset_dir, exist_ok=True)
        preset_data = {
            "name": name,
            "format": fmt,
            "settings": settings,
        }
        path = _preset_path(str(preset_dir), str(name))
        with open(path, "w") as fh:
            json.dump(preset_data, fh, indent=2)

        return success_result(
            "Export preset '{}' saved".format(name),
            prompt="Use apply_export_preset to apply this preset before exporting.",
            name=name,
            format=fmt,
            path=path,
        )
    except Exception as exc:
        return error_result("Failed to save export preset", str(exc))
