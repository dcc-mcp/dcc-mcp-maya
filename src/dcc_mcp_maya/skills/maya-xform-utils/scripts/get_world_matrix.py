"""Get the world-space transformation matrix of an object."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Get the world matrix (4x4) of the specified object.

    Args:
        params: Dictionary with keys:
            - name (str): Object name.
            - as_list (bool): If True, return as flat 16-element list. Default True.

    Returns:
        ActionResultModel with matrix data.
    """
    name = params.get("name", "")
    as_list = params.get("as_list", True)

    if not name:
        return error_result("Missing required parameter", "Parameter 'name' is required")

    try:
        if not cmds.objExists(name):
            return error_result("Object not found", "Object '{}' does not exist".format(name))

        matrix = cmds.getAttr("{}.worldMatrix[0]".format(name))  # type: List[float]
        # maya returns a flat list of 16 floats
        flat = list(matrix)

        if not as_list:
            # Return as 4x4 nested list
            mat4 = [flat[i * 4:(i + 1) * 4] for i in range(4)]
            return success_result(
                "World matrix retrieved for '{}'".format(name),
                prompt="Use decompose_matrix to extract translate/rotate/scale components.",
                matrix=mat4,
                name=name,
            )

        return success_result(
            "World matrix retrieved for '{}'".format(name),
            prompt="Use decompose_matrix to extract translate/rotate/scale components.",
            matrix=flat,
            name=name,
        )
    except Exception as exc:
        return error_result("Failed to get world matrix", str(exc))
