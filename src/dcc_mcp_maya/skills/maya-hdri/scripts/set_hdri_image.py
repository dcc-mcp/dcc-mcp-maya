"""Set or replace the HDRI image on an existing sky dome light."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Assign an HDRI image file to a sky dome light.

    Args:
        params: dict with keys:
            light (str): Sky dome light shape name (required).
            hdri_path (str): Path to HDRI/EXR image file (required).

    Returns:
        ActionResultModel with file node and connection info.
    """
    light = params.get("light", "")
    hdri_path = params.get("hdri_path", "")

    if not light:
        return error_result("Missing parameter", "'light' is required")
    if not hdri_path:
        return error_result("Missing parameter", "'hdri_path' is required")

    try:
        if not cmds.objExists(light):
            return error_result(
                "Light not found", "Node '{}' does not exist".format(light)
            )

        # Check if there is already a file node connected
        connections = cmds.listConnections(
            "{}.color".format(light), source=True, destination=False, type="file"
        )
        if connections:
            file_node = connections[0]
        else:
            file_node = cmds.shadingNode("file", asTexture=True, isColorManaged=True)
            cmds.connectAttr(
                "{}.outColor".format(file_node),
                "{}.color".format(light),
                force=True,
            )

        cmds.setAttr(
            "{}.fileTextureName".format(file_node), hdri_path, type="string"
        )

        return success_result(
            "HDRI image set on '{}'".format(light),
            prompt="Use set_sky_dome_attribute to adjust exposure or intensity.",
            light=light,
            file_node=file_node,
            hdri_path=hdri_path,
        )
    except Exception as exc:
        return error_result("Failed to set HDRI image", str(exc))
