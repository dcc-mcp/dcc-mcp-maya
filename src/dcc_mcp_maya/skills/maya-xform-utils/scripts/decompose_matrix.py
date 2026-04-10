"""Decompose a 4x4 matrix into translate, rotate, scale components."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Decompose an object's world matrix into TRS components via decomposeMatrix node.

    Args:
        params: Dictionary with keys:
            - name (str): Object name to decompose.
            - space (str): 'world' or 'local'. Default 'world'.

    Returns:
        ActionResultModel with translate/rotate/scale values.
    """
    name = params.get("name", "")
    space = params.get("space", "world")

    if not name:
        return error_result("Missing required parameter", "Parameter 'name' is required")

    try:
        if not cmds.objExists(name):
            return error_result("Object not found", "Object '{}' does not exist".format(name))

        if space == "world":
            translate = list(cmds.getAttr("{}.translate".format(name))[0])
            rotate = list(cmds.getAttr("{}.rotate".format(name))[0])
            scale = list(cmds.getAttr("{}.scale".format(name))[0])
            world_translate = cmds.xform(name, query=True, worldSpace=True, translation=True)
            world_rotate = cmds.xform(name, query=True, worldSpace=True, rotation=True)
            world_scale = cmds.xform(name, query=True, worldSpace=True, scale=True)
            return success_result(
                "Matrix decomposed for '{}' (world space)".format(name),
                prompt="Use set_transform to apply modified values back to the object.",
                name=name,
                space="world",
                translate=list(world_translate),
                rotate=list(world_rotate),
                scale=list(world_scale),
            )
        else:
            translate = list(cmds.getAttr("{}.translate".format(name))[0])
            rotate = list(cmds.getAttr("{}.rotate".format(name))[0])
            scale = list(cmds.getAttr("{}.scale".format(name))[0])
            return success_result(
                "Matrix decomposed for '{}' (local space)".format(name),
                prompt="Use set_transform to apply modified values back to the object.",
                name=name,
                space="local",
                translate=translate,
                rotate=rotate,
                scale=scale,
            )
    except Exception as exc:
        return error_result("Failed to decompose matrix", str(exc))
