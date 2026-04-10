"""Create a HumanIK character definition for motion capture retargeting."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Create a HumanIK character.

    Args:
        params: Dictionary with keys:
            - name (str): Character name. Default "Character1".
            - namespace (str): Optional namespace prefix.

    Returns:
        ActionResultModel with character node name.
    """
    name = params.get("name", "Character1")
    namespace = params.get("namespace", "")

    if not name:
        return error_result("Invalid parameter", "Character name must not be empty.")

    try:
        # Load HumanIK plugin
        if not cmds.pluginInfo("mayaHIK", query=True, loaded=True):
            cmds.loadPlugin("mayaHIK")

        full_name = "{0}:{1}".format(namespace, name) if namespace else name

        # Create HumanIK character node
        char_node = cmds.createNode("HIKCharacterNode", name="{0}_hikNode".format(full_name))
        cmds.setAttr("{0}.InputCharacterizationLock".format(char_node), False)

        return success_result(
            "Created HumanIK character '{0}'".format(full_name),
            prompt="Use define_hik_joint to map skeleton joints to the character definition.",
            character_node=char_node,
            character_name=full_name,
        )
    except Exception as exc:
        return error_result("Failed to create HumanIK character", str(exc))
