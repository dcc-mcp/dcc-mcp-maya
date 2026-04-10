"""List all aiSkyDomeLight nodes in the scene."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """List all sky dome light nodes in the scene.

    Args:
        params: dict (no required keys).

    Returns:
        ActionResultModel with list of sky dome info dicts.
    """
    try:
        dome_shapes = cmds.ls(type="aiSkyDomeLight") or []
        result: List[Dict] = []

        for shape in dome_shapes:
            transform = cmds.listRelatives(shape, parent=True)
            transform_name = transform[0] if transform else shape

            exposure = cmds.getAttr("{}.exposure".format(shape))
            intensity = cmds.getAttr("{}.intensity".format(shape))

            # Try to get connected HDRI path
            hdri_path = ""
            connections = cmds.listConnections(
                "{}.color".format(shape), source=True, type="file"
            )
            if connections:
                hdri_path = cmds.getAttr(
                    "{}.fileTextureName".format(connections[0])
                )

            result.append(
                {
                    "shape": shape,
                    "transform": transform_name,
                    "exposure": exposure,
                    "intensity": intensity,
                    "hdri_path": hdri_path,
                }
            )

        return success_result(
            "Found {} sky dome light(s)".format(len(result)),
            prompt="Use set_sky_dome_attribute to adjust exposure or set_hdri_image to change the HDRI file.",
            sky_domes=result,
            count=len(result),
        )
    except Exception as exc:
        return error_result("Failed to list sky dome lights", str(exc))
