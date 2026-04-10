"""Map a skeleton joint to a HumanIK bone slot."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

# Mapping of canonical bone names to HIK bone IDs (subset of common bones)
_HIK_BONE_IDS = {
    "Hips": 1,
    "LeftUpLeg": 2,
    "RightUpLeg": 3,
    "Spine": 4,
    "LeftLeg": 5,
    "RightLeg": 6,
    "Spine1": 7,
    "LeftFoot": 8,
    "RightFoot": 9,
    "Spine2": 10,
    "Neck": 13,
    "Head": 15,
    "LeftShoulder": 18,
    "RightShoulder": 19,
    "LeftArm": 20,
    "RightArm": 21,
    "LeftForeArm": 22,
    "RightForeArm": 23,
    "LeftHand": 24,
    "RightHand": 25,
}


def run(params: dict) -> object:
    """Map a joint to a HumanIK bone slot.

    Args:
        params: Dictionary with keys:
            - character_node (str): HIKCharacterNode name.
            - joint (str): Maya joint to map.
            - bone_name (str): Canonical HIK bone name (e.g. "Hips", "LeftArm").

    Returns:
        ActionResultModel with mapping result.
    """
    char_node = params.get("character_node", "")
    joint = params.get("joint", "")
    bone_name = params.get("bone_name", "")

    if not char_node:
        return error_result("Invalid parameter", "character_node must not be empty.")
    if not joint:
        return error_result("Invalid parameter", "joint must not be empty.")
    if bone_name not in _HIK_BONE_IDS:
        return error_result(
            "Unknown bone name '{0}'".format(bone_name),
            "Valid bones: {0}".format(", ".join(sorted(_HIK_BONE_IDS.keys()))),
        )

    try:
        bone_id = _HIK_BONE_IDS[bone_name]
        cmds.setAttr("{0}.InputChar{1}".format(char_node, bone_id), joint, type="string")
        return success_result(
            "Mapped joint '{0}' to HIK bone '{1}' (id={2})".format(joint, bone_name, bone_id),
            prompt="Continue mapping remaining joints, then lock the character definition.",
            character_node=char_node,
            joint=joint,
            bone_name=bone_name,
            bone_id=bone_id,
        )
    except Exception as exc:
        return error_result("Failed to define HIK joint", str(exc))
