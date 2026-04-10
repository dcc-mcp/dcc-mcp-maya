"""List light groups/rigs in the current scene."""
from __future__ import annotations

import logging
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)


def run(params: Dict[str, object]) -> object:
    """List all transform groups that contain lights.

    Args:
        params: Dictionary containing:
            - pattern (str): Name pattern to filter groups.  Default '' (all).

    Returns:
        ActionResultModel with rig groups list.
    """
    pattern = str(params.get("pattern", ""))

    try:
        # Find all light shapes
        light_types = [
            "spotLight", "directionalLight", "pointLight", "areaLight",
            "ambientLight", "volumeLight", "aiAreaLight", "aiSkyDomeLight",
        ]
        all_lights: List[str] = []
        for lt in light_types:
            all_lights.extend(cmds.ls(type=lt) or [])

        # Walk up to find groups containing lights
        rig_groups: Dict[str, List[str]] = {}
        for shape in all_lights:
            parents = cmds.listRelatives(shape, allParents=True, fullPath=True) or []
            for parent in parents:
                # Check grandparent (group level)
                gp_list = cmds.listRelatives(parent, parent=True, fullPath=True) or []
                for gp in gp_list:
                    gp_short = gp.split("|")[-1]
                    if pattern and pattern not in gp_short:
                        continue
                    if gp_short not in rig_groups:
                        rig_groups[gp_short] = []
                    light_short = shape.split("|")[-1]
                    if light_short not in rig_groups[gp_short]:
                        rig_groups[gp_short].append(light_short)

        rigs = [{"group": g, "lights": lts} for g, lts in rig_groups.items()]

        return success_result(
            "Found {} light rig group(s)".format(len(rigs)),
            prompt="Use set_light_attribute to adjust individual lights within a rig.",
            rigs=rigs,
            count=len(rigs),
        )
    except Exception as exc:
        logger.exception("list_light_rigs failed")
        return error_result("Failed to list light rigs", str(exc))
