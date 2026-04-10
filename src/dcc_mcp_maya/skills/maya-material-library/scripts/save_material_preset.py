"""Save a Maya material as a preset JSON file."""
from __future__ import annotations

import json
import os
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_material_presets")

# Common attributes to capture per shader type
_SHADER_ATTRS: Dict[str, List[str]] = {
    "lambert": ["color", "transparency", "ambientColor", "incandescence", "diffuse"],
    "blinn": ["color", "transparency", "specularColor", "eccentricity", "specularRollOff", "reflectivity"],
    "phong": ["color", "transparency", "specularColor", "cosinePower", "reflectivity"],
    "aiStandardSurface": ["baseColor", "base", "specularColor", "specular", "roughness", "metalness"],
}


def run(params: Dict[str, object]):
    """Save a material's attributes as a JSON preset.

    Args:
        params: Dictionary with keys:
            - material (str): Material node name. Required.
            - preset_name (str): Name for the preset file. Required.
            - preset_dir (str): Directory to save preset. Default ~/.maya_material_presets.

    Returns:
        ActionResultModel with saved preset path.
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

        shader_type = cmds.objectType(material)
        attr_list = _SHADER_ATTRS.get(shader_type, [])

        preset_data: Dict[str, object] = {"shader_type": shader_type, "attributes": {}}
        for attr in attr_list:
            full_attr = "{}.{}".format(material, attr)
            if cmds.objExists(full_attr):
                val = cmds.getAttr(full_attr)
                # Convert tuples/lists to plain lists for JSON serialisation
                if isinstance(val, list) and val and isinstance(val[0], tuple):
                    val = list(val[0])
                preset_data["attributes"][attr] = val

        os.makedirs(str(preset_dir), exist_ok=True)
        preset_path = os.path.join(str(preset_dir), "{}.json".format(preset_name))
        with open(preset_path, "w") as fh:
            json.dump(preset_data, fh, indent=2)

        return success_result(
            "Saved material preset '{}' ({})".format(preset_name, shader_type),
            prompt="Use apply_material_preset to apply this preset to other materials.",
            preset_name=preset_name,
            preset_path=preset_path,
            shader_type=shader_type,
            attribute_count=len(preset_data["attributes"]),
        )
    except Exception as exc:
        return error_result("Failed to save material preset", str(exc))
