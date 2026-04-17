"""Delete a Maya export preset JSON file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def delete_export_preset(preset_path: str) -> dict:
    """Delete a ``.json`` export preset file from disk.

    Args:
        preset_path: Full path to the ``.json`` preset file.

    Returns:
        ToolResult dict confirming deletion.
    """
    try:
        if not os.path.isfile(preset_path):
            return skill_error(
                "File not found",
                "Preset file '{}' does not exist".format(preset_path),
            )

        os.remove(preset_path)
        preset_name = os.path.splitext(os.path.basename(preset_path))[0]

        return skill_success(
            "Export preset deleted",
            prompt="Preset '{}' removed. Use save_export_preset to create a new one.".format(preset_name),
            deleted_path=preset_path,
            preset_name=preset_name,
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete export preset")


@skill_entry
def main(**kwargs):
    return delete_export_preset(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
