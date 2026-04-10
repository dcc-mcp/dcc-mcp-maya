"""Add a rim/back light to an existing light rig group."""
from __future__ import annotations

import logging
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """Add a rim light to an existing rig group.

    A rim light is positioned behind and above the subject to create a
    separation halo effect that helps distinguish the subject from the background.

    Args:
        params: Dictionary containing:
            - group (str): Rig group to add the light to.  Required.
            - light_name (str): Name for the new rim light.  Default 'rim_light'.
            - light_type (str): Light type ('spotLight', 'directionalLight',
                                'pointLight', 'areaLight').  Default 'spotLight'.
            - intensity (float): Light intensity.  Default 0.8.
            - position (list[float]): [x, y, z] world position.
                                      Default [0, 6, -10].

    Returns:
        ActionResultModel with new light transform and shape names.
    """
    group = str(params.get("group", "")).strip()
    light_name = str(params.get("light_name", "rim_light"))
    light_type = str(params.get("light_type", "spotLight"))
    intensity = float(params.get("intensity", 0.8))
    position_raw = params.get("position", [0.0, 6.0, -10.0])
    position = [float(v) for v in position_raw]  # type: ignore[union-attr]

    if not group:
        return error_result("Invalid parameters", "'group' is required.")

    valid_types = {"spotLight", "directionalLight", "pointLight", "areaLight"}
    if light_type not in valid_types:
        return error_result(
            "Invalid light type",
            "light_type must be one of {}.".format(sorted(valid_types)),
        )

    try:
        if not cmds.objExists(group):
            return error_result(
                "Group not found",
                "No node named '{}' exists.".format(group),
            )

        transform = cmds.createNode("transform", name=light_name, parent=group)
        shape = cmds.createNode(light_type, name="{}_shape".format(light_name), parent=transform)

        x, y, z = position[0], position[1], position[2] if len(position) > 2 else 0.0
        cmds.move(x, y, z, transform, absolute=True)

        if cmds.attributeQuery("intensity", node=shape, exists=True):
            cmds.setAttr("{}.intensity".format(shape), intensity)

        return success_result(
            "Added rim light '{}' to rig '{}'".format(light_name, group),
            prompt="Use set_rig_intensity to adjust the overall rig brightness.",
            transform=transform,
            shape=shape,
            group=group,
            intensity=intensity,
            position=position,
        )
    except Exception as exc:
        logger.exception("add_rim_light failed")
        return error_result(
            "Failed to add rim light '{}' to rig '{}'".format(light_name, group),
            str(exc),
        )
