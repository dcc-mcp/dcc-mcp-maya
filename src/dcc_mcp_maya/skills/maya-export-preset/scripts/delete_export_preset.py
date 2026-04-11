"""Delete a Maya export preset JSON file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def delete_export_preset(preset_path: str) -> dict:
    """Delete a ``.json`` export preset file from disk.

    Args:
        preset_path: Full path to the ``.json`` preset file.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    try:
        if not os.path.isfile(preset_path):
            return maya_error(
                "File not found",
                "Preset file '{}' does not exist".format(preset_path),
            )

        os.remove(preset_path)
        preset_name = os.path.splitext(os.path.basename(preset_path))[0]

        return maya_success(
            "Export preset deleted",
            prompt="Preset '{}' removed. Use save_export_preset to create a new one.".format(preset_name),
            deleted_path=preset_path,
            preset_name=preset_name,
        )
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete export preset")


def main(**kwargs):
    return delete_export_preset(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_export_preset("/path/to/preset.json")
    print(json.dumps(result))
