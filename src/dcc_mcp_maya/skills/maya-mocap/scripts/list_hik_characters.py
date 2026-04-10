"""List all HumanIK characters in the current scene."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """List all HIKCharacterNode nodes in the scene.

    Args:
        params: Unused — no parameters required.

    Returns:
        ActionResultModel with list of character node names.
    """
    try:
        char_nodes = cmds.ls(type="HIKCharacterNode") or []
        characters = []
        for node in char_nodes:
            locked = cmds.getAttr("{0}.InputCharacterizationLock".format(node))
            characters.append({"node": node, "locked": bool(locked)})

        return success_result(
            "Found {0} HumanIK character(s)".format(len(characters)),
            prompt=(
                "Use define_hik_joint to map joints, or retarget_mocap to apply"
                " animation data to a character."
            ),
            characters=characters,
            count=len(characters),
        )
    except Exception as exc:
        return error_result("Failed to list HIK characters", str(exc))
