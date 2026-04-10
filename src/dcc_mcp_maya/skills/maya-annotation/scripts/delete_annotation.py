"""Delete an annotation node from the scene."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Delete an annotation node (transform + shape).

    Args:
        params: Dictionary with keys:
            - name (str): Annotation transform or shape node name to delete.

    Returns:
        ActionResultModel.
    """
    name = params.get("name", "")

    if not name:
        return error_result("Missing required parameter", "Parameter 'name' is required")

    try:
        if not cmds.objExists(str(name)):
            return error_result("Node not found", "Annotation '{}' does not exist".format(name))

        node_type = cmds.objectType(str(name))
        if node_type not in ("annotationShape", "transform"):
            return error_result(
                "Invalid node type",
                "'{}' is a '{}', expected annotationShape or transform".format(name, node_type),
            )

        # Delete the transform (which removes the shape too)
        if node_type == "annotationShape":
            parents = cmds.listRelatives(str(name), parent=True, fullPath=False) or []
            to_delete = parents[0] if parents else str(name)
        else:
            to_delete = str(name)

        cmds.delete(to_delete)

        return success_result(
            "Deleted annotation '{}'".format(name),
            prompt="Use list_annotations to view remaining annotations.",
            name=name,
        )
    except Exception as exc:
        return error_result("Failed to delete annotation", str(exc))
