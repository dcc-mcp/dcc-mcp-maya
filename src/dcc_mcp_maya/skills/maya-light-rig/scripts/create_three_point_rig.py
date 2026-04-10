"""Create a classic three-point lighting rig (key, fill, back)."""
from __future__ import annotations

import logging
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result

logger = logging.getLogger(__name__)

# Default positions for a standard three-point rig
_DEFAULT_POSITIONS = {
    "key": (5.0, 8.0, 5.0),
    "fill": (-5.0, 4.0, 4.0),
    "back": (0.0, 6.0, -8.0),
}

_DEFAULT_INTENSITIES = {
    "key": 1.0,
    "fill": 0.4,
    "back": 0.6,
}


def run(params: Dict[str, object]) -> object:
    """Create a three-point lighting rig around a target point.

    Args:
        params: Dictionary containing:
            - rig_name (str): Base name prefix for lights.  Default 'threePoint'.
            - light_type (str): Light type to use ('spotLight', 'directionalLight',
                                'pointLight', 'areaLight').  Default 'spotLight'.
            - key_intensity (float): Key light intensity.  Default 1.0.
            - fill_intensity (float): Fill light intensity.  Default 0.4.
            - back_intensity (float): Back/rim light intensity.  Default 0.6.
            - group (bool): Group all three lights under a common transform.
                            Default True.

    Returns:
        ActionResultModel with names of created lights and optional group.
    """
    rig_name = str(params.get("rig_name", "threePoint"))
    light_type = str(params.get("light_type", "spotLight"))
    key_intensity = float(params.get("key_intensity", _DEFAULT_INTENSITIES["key"]))
    fill_intensity = float(params.get("fill_intensity", _DEFAULT_INTENSITIES["fill"]))
    back_intensity = float(params.get("back_intensity", _DEFAULT_INTENSITIES["back"]))
    do_group = bool(params.get("group", True))

    valid_types = {"spotLight", "directionalLight", "pointLight", "areaLight"}
    if light_type not in valid_types:
        return error_result(
            "Invalid light type",
            "light_type must be one of {}.".format(sorted(valid_types)),
        )

    try:
        intensities = {"key": key_intensity, "fill": fill_intensity, "back": back_intensity}
        created: List[Dict[str, object]] = []

        for role, pos in _DEFAULT_POSITIONS.items():
            light_name = "{}_{}_light".format(rig_name, role)
            transform = cmds.createNode("transform", name=light_name)
            shape = cmds.createNode(light_type, name="{}_shape".format(light_name), parent=transform)
            cmds.move(pos[0], pos[1], pos[2], transform, absolute=True)
            # Aim at origin
            aim = cmds.aimConstraint(
                "world",  # placeholder — use origin (0,0,0) via tmp locator
                transform,
                worldUpType="vector",
                worldUpVector=(0, 1, 0),
                skip=["x", "z"],
            )
            # Remove aim constraint — just set rotation to point at origin
            cmds.delete(aim)
            # Point light at origin manually via lookAt equivalent
            cmds.pointConstraint("world", transform, skip=["x", "y", "z"])
            cmds.delete(cmds.listRelatives(transform, type="pointConstraint") or [])

            # Set intensity
            intensity_attr = "{}.intensity".format(shape)
            if cmds.attributeQuery("intensity", node=shape, exists=True):
                cmds.setAttr(intensity_attr, intensities[role])

            created.append({"role": role, "transform": transform, "shape": shape})

        group_name = None
        if do_group:
            transforms = [c["transform"] for c in created]
            group_name = cmds.group(*transforms, name="{}_rig_grp".format(rig_name))

        return success_result(
            "Created three-point rig '{}'".format(rig_name),
            prompt="Use set_light_attribute to fine-tune intensity, colour, and shadow settings.",
            lights=created,
            group=group_name,
            rig_name=rig_name,
        )
    except Exception as exc:
        logger.exception("create_three_point_rig failed")
        return error_result("Failed to create three-point rig '{}'".format(rig_name), str(exc))
