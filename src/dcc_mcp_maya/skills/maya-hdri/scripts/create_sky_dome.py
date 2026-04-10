"""Create an Arnold skydome light for HDRI/IBL lighting."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Create an aiSkyDomeLight node for IBL.

    Args:
        params: dict with keys:
            name (str): Light node name. Default "aiSkyDomeLight1".
            hdri_path (str): Optional path to HDRI image file.
            exposure (float): Exposure value. Default 0.0.
            intensity (float): Intensity multiplier. Default 1.0.

    Returns:
        ActionResultModel with light node name.
    """
    name = params.get("name", "aiSkyDomeLight1")
    hdri_path = params.get("hdri_path", "")
    exposure = float(params.get("exposure", 0.0))
    intensity = float(params.get("intensity", 1.0))

    try:
        # Load Arnold plugin if not loaded
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            cmds.loadPlugin("mtoa")

        light_shape, light_transform = cmds.shadingNode(
            "aiSkyDomeLight", asLight=True, name=name
        )

        cmds.setAttr("{}.exposure".format(light_shape), exposure)
        cmds.setAttr("{}.intensity".format(light_shape), intensity)

        if hdri_path:
            # Create file texture node and connect to color
            file_node = cmds.shadingNode("file", asTexture=True, isColorManaged=True)
            cmds.setAttr("{}.fileTextureName".format(file_node), hdri_path, type="string")
            cmds.connectAttr(
                "{}.outColor".format(file_node),
                "{}.color".format(light_shape),
                force=True,
            )

        return success_result(
            "Created sky dome light '{}'".format(light_transform),
            prompt="Use set_hdri_image to assign an HDRI file, or set_sky_dome_attribute to adjust parameters.",
            light_transform=light_transform,
            light_shape=light_shape,
            exposure=exposure,
            intensity=intensity,
            hdri_path=hdri_path,
        )
    except Exception as exc:
        return error_result("Failed to create sky dome light", str(exc))
