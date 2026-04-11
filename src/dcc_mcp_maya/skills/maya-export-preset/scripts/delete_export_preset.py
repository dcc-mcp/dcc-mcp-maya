"""Delete a Maya export preset JSON file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os

logger = logging.getLogger(__name__)


def delete_export_preset(preset_path: str) -> dict:
    """Delete a ``.json`` export preset file from disk.

    Args:
        preset_path: Full path to the ``.json`` preset file.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        if not os.path.isfile(preset_path):
            return error_result(
                "File not found",
                "Preset file '{}' does not exist".format(preset_path),
            ).to_dict()

        os.remove(preset_path)
        preset_name = os.path.splitext(os.path.basename(preset_path))[0]

        return success_result(
            "Export preset deleted",
            prompt="Preset '{}' removed. Use save_export_preset to create a new one.".format(preset_name),
            deleted_path=preset_path,
            preset_name=preset_name,
        ).to_dict()
    except Exception as exc:
        logger.exception("delete_export_preset failed")
        return error_result("Failed to delete export preset", str(exc)).to_dict()


def main(**kwargs):
    return delete_export_preset(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_export_preset("/path/to/preset.json")
    print(json.dumps(result))
