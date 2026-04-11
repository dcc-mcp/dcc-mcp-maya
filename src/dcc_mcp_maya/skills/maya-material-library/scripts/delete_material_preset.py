"""Remove a material preset file from the library."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def delete_material_preset(file_path: str) -> dict:
    """Delete a material preset JSON file from the library.

    Args:
        file_path: Absolute path to the ``.json`` preset file to remove.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    try:
        if not os.path.isfile(file_path):
            return maya_error(
                "Preset file not found: '{}'".format(file_path),
                "Use list_materials to find available preset paths",
            )

        os.remove(file_path)
        name = os.path.splitext(os.path.basename(file_path))[0]

        return maya_success(
            "Deleted material preset '{}'".format(name),
            prompt="Use list_materials to verify the preset has been removed.",
            file_path=file_path,
            preset_name=name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete preset '{}'".format(file_path))


def main(**kwargs):
    return delete_material_preset(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_material_preset("/tmp/mat_lib/lambert1.json")))
