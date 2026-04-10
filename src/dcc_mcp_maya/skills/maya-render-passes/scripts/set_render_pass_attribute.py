"""Set an attribute on a render pass node."""
from __future__ import annotations

import logging
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Set a scalar, string, or list attribute on a renderPass node.

    Args:
        params: Dictionary containing:
            - name (str): Name of the renderPass node.  Required.
            - attribute (str): Attribute name.  Required.
            - value: New value (string / number / list).  Required.

    Returns:
        ActionResultModel confirming the attribute change.
    """
    name = str(params.get("name", "")).strip()
    attribute = str(params.get("attribute", "")).strip()
    value = params.get("value")

    if not name:
        return error_result("Invalid parameters", "'name' is required.")
    if not attribute:
        return error_result("Invalid parameters", "'attribute' is required.")
    if value is None:
        return error_result("Invalid parameters", "'value' is required.")

    try:
        if not cmds.objExists(name):
            return error_result(
                "Render pass not found",
                "No node named '{}' exists.".format(name),
            )

        attr_path = "{}.{}".format(name, attribute)
        if isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        elif isinstance(value, (list, tuple)):
            values: List[float] = [float(v) for v in value]  # type: ignore[arg-type]
            cmds.setAttr(attr_path, *values)
        else:
            cmds.setAttr(attr_path, value)

        return success_result(
            "Set '{}.{}' to {}".format(name, attribute, value),
            prompt="Use list_render_passes to verify the updated attribute.",
            node=name,
            attribute=attribute,
            value=value,
        )
    except Exception as exc:
        logger.exception("set_render_pass_attribute failed")
        return error_result(
            "Failed to set attribute '{}.{}'".format(name, attribute),
            str(exc),
        )
