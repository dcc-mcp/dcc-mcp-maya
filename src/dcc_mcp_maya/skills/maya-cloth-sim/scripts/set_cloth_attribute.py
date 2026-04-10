"""Set an attribute on an nCloth node."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Set a numeric or string attribute on an nCloth node.

    Args:
        params: Dictionary with keys:
            - cloth_node (str): nCloth node name.
            - attribute (str): Attribute to set.
            - value (float | str | list): Value to assign.

    Returns:
        ActionResultModel with set result.
    """
    cloth_node = params.get("cloth_node", "")
    attribute = params.get("attribute", "")
    value = params.get("value", None)

    if not cloth_node:
        return error_result("Invalid parameter", "cloth_node must not be empty.")
    if not attribute:
        return error_result("Invalid parameter", "attribute must not be empty.")
    if value is None:
        return error_result("Invalid parameter", "value must be provided.")

    try:
        if not cmds.objExists(cloth_node):
            return error_result("Node not found", "'{0}' does not exist.".format(cloth_node))
        if cmds.nodeType(cloth_node) != "nCloth":
            return error_result(
                "Invalid node type",
                "Expected nCloth, got {0}.".format(cmds.nodeType(cloth_node)),
            )

        attr_path = "{0}.{1}".format(cloth_node, attribute)
        if isinstance(value, list):
            cmds.setAttr(attr_path, *value)
        elif isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {0}.{1} = {2}".format(cloth_node, attribute, value),
            prompt="Attribute updated. Re-simulate with simulate_cloth to see the effect.",
            cloth_node=cloth_node,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return error_result("Failed to set cloth attribute", str(exc))
