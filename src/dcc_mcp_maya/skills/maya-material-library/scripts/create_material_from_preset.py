"""Create a new material node from a preset and optionally assign it."""
from __future__ import annotations

import json
import os
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

_PRESET_DIR = os.path.join(os.path.expanduser("~"), ".maya_material_presets")


def run(params: Dict[str, object]):
    """Create a new material from a preset and optionally assign to objects.

    Args:
        params: Dictionary with keys:
            - preset_name (str): Name of the preset to use. Required.
            - material_name (str): Name for the new material. Optional.
            - assign_to (list): Object names to assign the material to. Optional.
            - preset_dir (str): Directory containing presets. Default ~/.maya_material_presets.

    Returns:
        ActionResultModel with new material node name.
    """
    preset_name = params.get("preset_name", "")
    material_name = params.get("material_name", "")
    assign_to = params.get("assign_to", [])
    preset_dir = params.get("preset_dir", _PRESET_DIR)

    if not preset_name:
        return error_result("Missing required parameter", "Parameter 'preset_name' is required")

    try:
        preset_path = os.path.join(str(preset_dir), "{}.json".format(preset_name))
        if not os.path.isfile(preset_path):
            return error_result(
                "Preset not found", "No preset file at: {}".format(preset_path)
            )

        with open(preset_path) as fh:
            preset_data = json.load(fh)

        shader_type = preset_data.get("shader_type", "lambert")
        new_mat = cmds.shadingNode(
            shader_type, asShader=True,
            name=str(material_name) if material_name else "{}_mat".format(preset_name),
        )
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}_SG".format(new_mat))
        cmds.connectAttr("{}.outColor".format(new_mat), "{}.surfaceShader".format(sg), force=True)

        applied = 0
        for attr, val in preset_data.get("attributes", {}).items():
            full_attr = "{}.{}".format(new_mat, attr)
            if not cmds.objExists(full_attr):
                continue
            if isinstance(val, list):
                cmds.setAttr(full_attr, *val, type="double3")
            else:
                cmds.setAttr(full_attr, val)
            applied += 1

        assigned: List[str] = []
        for obj in list(assign_to):
            if cmds.objExists(str(obj)):
                cmds.sets(str(obj), edit=True, forceElement=sg)
                assigned.append(str(obj))

        return success_result(
            "Created material '{}' from preset '{}'".format(new_mat, preset_name),
            prompt="Use assign_material or set_material_attribute to further customise.",
            material=new_mat,
            shading_group=sg,
            shader_type=shader_type,
            applied_count=applied,
            assigned_objects=assigned,
        )
    except Exception as exc:
        return error_result("Failed to create material from preset", str(exc))
