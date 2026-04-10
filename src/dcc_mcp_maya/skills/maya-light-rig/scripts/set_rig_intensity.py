"""Set the intensity of all lights in a rig group by a multiplier."""
from __future__ import annotations

import logging
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)

_LIGHT_TYPES = [
    "spotLight", "directionalLight", "pointLight", "areaLight",
    "ambientLight", "volumeLight", "aiAreaLight",
]


def run(params: Dict[str, object]) -> object:
    """Multiply all light intensities inside a group by a given factor.

    Args:
        params: Dictionary containing:
            - group (str): Name of the light rig group transform.  Required.
            - multiplier (float): Intensity multiplier.  Default 1.0.
            - absolute (float | None): If provided, set all lights to this
                                       absolute intensity instead.  Default None.

    Returns:
        ActionResultModel with updated lights and their new intensities.
    """
    group = str(params.get("group", "")).strip()
    multiplier = float(params.get("multiplier", 1.0))
    absolute = params.get("absolute")

    if not group:
        return error_result("Invalid parameters", "'group' is required.")

    try:
        if not cmds.objExists(group):
            return error_result(
                "Group not found",
                "No node named '{}' exists.".format(group),
            )

        # Gather all light shapes under the group
        descendants = cmds.listRelatives(group, allDescendants=True, fullPath=True) or []
        light_shapes: List[str] = []
        for node in descendants:
            if cmds.nodeType(node) in _LIGHT_TYPES:
                light_shapes.append(node)

        if not light_shapes:
            return error_result(
                "No lights found",
                "Group '{}' contains no recognised light shapes.".format(group),
            )

        updated: List[Dict[str, object]] = []
        for shape in light_shapes:
            if not cmds.attributeQuery("intensity", node=shape, exists=True):
                continue
            if absolute is not None:
                new_val = float(absolute)
            else:
                current = cmds.getAttr("{}.intensity".format(shape))
                new_val = current * multiplier
            cmds.setAttr("{}.intensity".format(shape), new_val)
            updated.append({"shape": shape, "intensity": new_val})

        return success_result(
            "Updated {} light(s) in rig '{}'".format(len(updated), group),
            prompt="Use list_light_rigs to review the rig configuration.",
            group=group,
            updated_lights=updated,
        )
    except Exception as exc:
        logger.exception("set_rig_intensity failed")
        return error_result("Failed to set rig intensity for '{}'".format(group), str(exc))
