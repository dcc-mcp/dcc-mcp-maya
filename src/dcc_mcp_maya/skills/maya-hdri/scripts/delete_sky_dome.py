"""Delete an aiSkyDomeLight node and its transform."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Delete a sky dome light (shape + transform).

    Args:
        params: dict with keys:
            light (str): Sky dome light shape or transform name (required).
            delete_file_nodes (bool): Also delete connected file texture nodes. Default False.

    Returns:
        ActionResultModel with deletion status.
    """
    light = params.get("light", "")
    delete_file_nodes = bool(params.get("delete_file_nodes", False))

    if not light:
        return error_result("Missing parameter", "'light' is required")

    try:
        if not cmds.objExists(light):
            return error_result(
                "Light not found", "Node '{}' does not exist".format(light)
            )

        # Validate type: accept shape or transform
        node_type = cmds.nodeType(light)
        if node_type == "aiSkyDomeLight":
            shape = light
            transforms = cmds.listRelatives(shape, parent=True) or []
            transform = transforms[0] if transforms else None
        elif node_type == "transform":
            transform = light
            shapes = cmds.listRelatives(light, shapes=True, type="aiSkyDomeLight") or []
            shape = shapes[0] if shapes else None
        else:
            return error_result(
                "Invalid node type",
                "Expected aiSkyDomeLight or its transform, got '{}'".format(node_type),
            )

        # Collect file nodes before deletion
        file_nodes = []
        if delete_file_nodes and shape:
            connections = cmds.listConnections(
                "{}.color".format(shape), source=True, type="file"
            )
            if connections:
                file_nodes = connections

        # Delete transform (deletes shape too)
        if transform and cmds.objExists(transform):
            cmds.delete(transform)
        elif shape and cmds.objExists(shape):
            cmds.delete(shape)

        for fn in file_nodes:
            if cmds.objExists(fn):
                cmds.delete(fn)

        return success_result(
            "Deleted sky dome light '{}'".format(light),
            prompt="Use create_sky_dome to add a new HDRI light.",
            deleted=light,
            deleted_file_nodes=file_nodes,
        )
    except Exception as exc:
        return error_result("Failed to delete sky dome light", str(exc))
