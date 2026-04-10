"""Set an attribute on an aiSkyDomeLight shape node."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Set a named attribute on a sky dome light.

    Args:
        params: dict with keys:
            light (str): Sky dome light shape name (required).
            attribute (str): Attribute name, e.g. 'exposure', 'intensity', 'skyRadius' (required).
            value: New value (numeric or string).

    Returns:
        ActionResultModel with updated attribute info.
    """
    light = params.get("light", "")
    attribute = params.get("attribute", "")
    value = params.get("value")

    if not light:
        return error_result("Missing parameter", "'light' is required")
    if not attribute:
        return error_result("Missing parameter", "'attribute' is required")
    if value is None:
        return error_result("Missing parameter", "'value' is required")

    try:
        if not cmds.objExists(light):
            return error_result(
                "Light not found", "Node '{}' does not exist".format(light)
            )

        attr_path = "{}.{}".format(light, attribute)
        if isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        elif isinstance(value, (list, tuple)):
            cmds.setAttr(attr_path, *value)
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set {}.{} = {}".format(light, attribute, value),
            prompt="Adjust other attributes or render to see the lighting change.",
            light=light,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        return error_result(
            "Failed to set attribute '{}'".format(attribute), str(exc)
        )
