"""Remove a material preset file from the library."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def delete_material_preset(file_path: str) -> dict:
    """Delete a material preset JSON file from the library.

    Args:
        file_path: Absolute path to the ``.json`` preset file to remove.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    try:
        if not os.path.isfile(file_path):
            return skill_error(
                "Preset file not found: '{}'".format(file_path),
                "Use list_materials to find available preset paths",
            )

        os.remove(file_path)
        name = os.path.splitext(os.path.basename(file_path))[0]

        return skill_success(
            "Deleted material preset '{}'".format(name),
            prompt="Use list_materials to verify the preset has been removed.",
            file_path=file_path,
            preset_name=name,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete preset '{}'".format(file_path))


@skill_entry
def main(**kwargs):
    return delete_material_preset(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
