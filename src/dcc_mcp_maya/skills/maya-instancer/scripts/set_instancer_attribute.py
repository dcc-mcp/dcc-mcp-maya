"""Set attributes on a Particle Instancer node."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Set an attribute on an instancer node.

    Args:
        params: Dictionary containing:
            - instancer (str): Name of the instancer node. Required.
            - attribute (str): Attribute name (e.g. 'cycle', 'rotationOrder'). Required.
            - value: New value. Scalar, string, or list for compound attrs.

    Returns:
        ActionResultModel confirming the attribute was set.
    """
    instancer = params.get("instancer", "")
    attribute = params.get("attribute", "")
    value = params.get("value")

    if not instancer or not attribute:
        return error_result(
            "Invalid parameters",
            "Both 'instancer' and 'attribute' are required.",
        )
    if value is None:
        return error_result("Invalid parameters", "Parameter 'value' is required.")

    try:
        if not cmds.objExists(instancer):
            return error_result(
                "Instancer not found",
                "No node named '{}' in the scene.".format(instancer),
            )
        attr_path = "{}.{}".format(instancer, attribute)
        if isinstance(value, (list, tuple)):
            values: List[object] = list(value)
            cmds.setAttr(attr_path, *values)
        elif isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        else:
            cmds.setAttr(attr_path, value)
        return success_result(
            "Set {}.{} = {}".format(instancer, attribute, value),
            prompt="Use list_instancers to inspect updated instancer state.",
            instancer=instancer,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return error_result("Failed to set instancer attribute", str(exc))
