"""Apply a material preset to a Maya material node."""
from __future__ import annotations

import json
import os
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_material_presets")


def run(params: Dict[str, object]):
    """Apply a saved material preset to an existing material node.

    Args:
        params: Dictionary with keys:
            - material (str): Target material node name. Required.
            - preset_name (str): Name of the preset to apply. Required.
            - preset_dir (str): Directory containing presets. Default ~/.maya_material_presets.

    Returns:
        ActionResultModel with applied attributes count.
    """
    material = params.get("material", "")
    preset_name = params.get("preset_name", "")
    preset_dir = params.get("preset_dir", _PRESET_DIR)

    if not material:
        return error_result("Missing required parameter", "Parameter 'material' is required")
    if not preset_name:
        return error_result("Missing required parameter", "Parameter 'preset_name' is required")

    try:
        material = str(material)
        if not cmds.objExists(material):
            return error_result("Material not found", "Material '{}' does not exist".format(material))

        preset_path = os.path.join(str(preset_dir), "{}.json".format(preset_name))
        if not os.path.isfile(preset_path):
            return error_result(
                "Preset not found", "No preset file at: {}".format(preset_path)
            )

        with open(preset_path) as fh:
            preset_data = json.load(fh)

        applied = 0
        for attr, val in preset_data.get("attributes", {}).items():
            full_attr = "{}.{}".format(material, attr)
            if not cmds.objExists(full_attr):
                continue
            if isinstance(val, list):
                cmds.setAttr(full_attr, *val, type="double3")
            else:
                cmds.setAttr(full_attr, val)
            applied += 1

        return success_result(
            "Applied preset '{}' to '{}' ({} attributes)".format(preset_name, material, applied),
            prompt="Use list_material_presets to see all available presets.",
            material=material,
            preset_name=preset_name,
            applied_count=applied,
        )
    except Exception as exc:
        return error_result("Failed to apply material preset", str(exc))
