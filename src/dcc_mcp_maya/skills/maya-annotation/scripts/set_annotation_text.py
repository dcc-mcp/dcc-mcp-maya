"""Update the text of an existing annotation node."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def _find_annotation_shape(node_name: str) -> str:
    """Return annotation shape node under the given transform."""
    shapes = cmds.listRelatives(node_name, shapes=True, fullPath=False) or []
    for shape in shapes:
        if cmds.objectType(shape) == "annotationShape":
            return shape
    return ""


def run(params: Dict[str, object]):
    """Set the display text of an annotation node.

    Args:
        params: Dictionary with keys:
            - name (str): Annotation transform or shape node name.
            - text (str): New text to set.

    Returns:
        ActionResultModel.
    """
    name = params.get("name", "")
    text = params.get("text", "")

    if not name:
        return error_result("Missing required parameter", "Parameter 'name' is required")
    if not text:
        return error_result("Missing required parameter", "Parameter 'text' is required")

    try:
        if not cmds.objExists(str(name)):
            return error_result("Node not found", "Annotation '{}' does not exist".format(name))

        node_type = cmds.objectType(str(name))
        if node_type == "annotationShape":
            shape = str(name)
        elif node_type == "transform":
            shape = _find_annotation_shape(str(name))
            if not shape:
                return error_result(
                    "No annotation shape",
                    "'{}' has no annotationShape child".format(name),
                )
        else:
            return error_result(
                "Invalid node type",
                "'{}' is a '{}', not an annotation node".format(name, node_type),
            )

        cmds.setAttr("{}.text".format(shape), str(text), type="string")

        return success_result(
            "Annotation text updated on '{}'".format(name),
            prompt="Annotation is visible in the viewport.",
            name=name,
            text=text,
        )
    except Exception as exc:
        return error_result("Failed to set annotation text", str(exc))
