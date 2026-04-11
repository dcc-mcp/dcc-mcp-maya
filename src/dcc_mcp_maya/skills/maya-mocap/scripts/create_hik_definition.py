"""Create a HumanIK character definition and map joints for retargeting."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Dict

# Minimal HumanIK slot -> slot ID mapping
_HIK_SLOTS = {
    "Reference": 0,
    "Hips": 1,
    "LeftUpLeg": 2,
    "LeftLeg": 3,
    "LeftFoot": 4,
    "RightUpLeg": 5,
    "RightLeg": 6,
    "RightFoot": 7,
    "Spine": 8,
    "LeftArm": 9,
    "LeftForeArm": 10,
    "LeftHand": 11,
    "RightArm": 12,
    "RightForeArm": 13,
    "RightHand": 14,
    "Head": 15,
    "LeftToeBase": 16,
    "RightToeBase": 17,
    "LeftShoulder": 18,
    "RightShoulder": 19,
    "Neck": 20,
    "Chest": 23,
}


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def create_hik_definition(
    character_name: str,
    joint_mapping: Dict[str, str],
) -> dict:
    """Create HumanIK character and map joints.

    Args:
        character_name: Name for the HIK character definition.
        joint_mapping: Dict of HIK slot name -> scene joint name,
            e.g. ``{"Hips": "mixamorig:Hips", "Spine": "mixamorig:Spine"}``.

    Returns:
        ActionResultModel dict with ``context.character_node``, ``context.mapped``,
        ``context.skipped``, and ``context.mapped_count``.
    """

    if not character_name:
        return maya_error("Missing parameter", "'character_name' is required")
    if not joint_mapping:
        return maya_error("Missing parameter", "'joint_mapping' is required")

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        cmds.loadPlugin("mayaHIK", quiet=True)
        mel.eval("HIKCharacterControlsTool")

        char_node = mel.eval('hikCreateCharacter("{}")'.format(character_name))

        mapped = []
        skipped = []
        for slot_name, joint_name in joint_mapping.items():
            slot_id = _HIK_SLOTS.get(slot_name)
            if slot_id is None:
                skipped.append({"slot": slot_name, "reason": "Unknown HIK slot"})
                continue
            if not cmds.objExists(joint_name):
                skipped.append({"slot": slot_name, "joint": joint_name, "reason": "Joint not found"})
                continue
            mel.eval('setCharacterObject("{}", "{}", {}, 0)'.format(joint_name, char_node, slot_id))
            mapped.append({"slot": slot_name, "joint": joint_name})

        mel.eval("hikUpdateDefinitionUI")

        return maya_success(
            "HIK character '{}' created with {} mapped joints".format(char_node, len(mapped)),
            prompt="HIK definition ready. Use bake_mocap_to_rig to retarget the motion.",
            character_node=char_node,
            mapped=mapped,
            skipped=skipped,
            mapped_count=len(mapped),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create HIK definition")


def main(**kwargs):
    return create_hik_definition(**kwargs)


if __name__ == "__main__":
    import json

    result = create_hik_definition("myChar", {"Hips": "Hips"})
    print(json.dumps(result))
