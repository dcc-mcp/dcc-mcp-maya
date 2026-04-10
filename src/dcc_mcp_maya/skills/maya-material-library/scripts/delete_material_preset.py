"""Remove a material preset file from the library."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os

logger = logging.getLogger(__name__)


def delete_material_preset(file_path: str) -> dict:
    """Delete a material preset JSON file from the library.

    Args:
        file_path: Absolute path to the ``.json`` preset file to remove.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        if not os.path.isfile(file_path):
            return error_result(
                "Preset file not found: '{}'".format(file_path),
                "Use list_materials to find available preset paths",
            ).to_dict()

        os.remove(file_path)
        name = os.path.splitext(os.path.basename(file_path))[0]

        return success_result(
            "Deleted material preset '{}'".format(name),
            prompt="Use list_materials to verify the preset has been removed.",
            file_path=file_path,
            preset_name=name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_material_preset failed")
        return error_result("Failed to delete preset '{}'".format(file_path), str(exc)).to_dict()


def main(**kwargs):
    return delete_material_preset(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_material_preset("/tmp/mat_lib/lambert1.json")))
