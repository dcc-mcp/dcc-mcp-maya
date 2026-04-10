"""Create a skydome / environment light from an HDR image."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_hdri_dome(
    hdri_path: str,
    name: Optional[str] = None,
    intensity: float = 1.0,
    rotation: float = 0.0,
    visible_in_diffuse: bool = True,
    visible_in_specular: bool = True,
) -> dict:
    """Create a skydome / environment light from an HDR image.

    Attempts to create an Arnold ``aiSkyDomeLight`` first.  Falls back to a
    Maya ``envFog`` + ``file`` texture node for non-Arnold scenes.

    Args:
        hdri_path: Absolute path to the ``.hdr`` or ``.exr`` file.
        name: Optional name for the skydome transform node.
        intensity: Light intensity multiplier.  Default: 1.0.
        rotation: Y-axis rotation in degrees for the HDRI map.  Default: 0.0.
        visible_in_diffuse: Enable diffuse contribution.  Default: True.
        visible_in_specular: Enable specular contribution.  Default: True.

    Returns:
        ActionResultModel dict with ``context.dome_node``,
        ``context.file_node``, ``context.hdri_path``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        node_name = name or "hdri_dome"
        dome_transform = None
        dome_shape = None
        file_node = None

        if cmds.pluginInfo("mtoa", loaded=True, query=True):
            dome_transform = cmds.createNode("transform", name=node_name)
            dome_shape = cmds.createNode("aiSkyDomeLight", name="{}_Shape".format(node_name), parent=dome_transform)
            cmds.setAttr("{}.intensity".format(dome_shape), intensity)
            cmds.setAttr("{}.rotateY".format(dome_transform), rotation)

            file_node = cmds.createNode("file", name="{}_texture".format(node_name))
            cmds.setAttr("{}.fileTextureName".format(file_node), hdri_path, type="string")
            cmds.setAttr("{}.colorSpace".format(file_node), "scene-linear Rec.709-sRGB", type="string")

            color_port = "{}.color".format(dome_shape)
            out_color = "{}.outColor".format(file_node)
            cmds.connectAttr(out_color, color_port, force=True)

            if cmds.attributeQuery("aiDiffuse", node=dome_shape, exists=True):
                cmds.setAttr("{}.aiDiffuse".format(dome_shape), int(visible_in_diffuse))
            if cmds.attributeQuery("aiSpecular", node=dome_shape, exists=True):
                cmds.setAttr("{}.aiSpecular".format(dome_shape), int(visible_in_specular))
        else:
            dome_transform = cmds.createNode("transform", name=node_name)
            dome_shape = cmds.createNode("ambientLight", name="{}_Shape".format(node_name), parent=dome_transform)
            cmds.setAttr("{}.intensity".format(dome_shape), intensity)

            file_node = cmds.createNode("file", name="{}_texture".format(node_name))
            cmds.setAttr("{}.fileTextureName".format(file_node), hdri_path, type="string")

        return success_result(
            "Created HDRI dome '{}' from '{}'".format(dome_transform, hdri_path),
            prompt="Adjust intensity with set_light_rig_intensity or rotate the dome to change HDRI orientation.",
            dome_node=dome_transform,
            dome_shape=dome_shape,
            file_node=file_node,
            hdri_path=hdri_path,
            intensity=intensity,
            rotation=rotation,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_hdri_dome failed")
        return error_result("Failed to create HDRI dome from '{}'".format(hdri_path), str(exc)).to_dict()


def main(**kwargs):
    return create_hdri_dome(**kwargs)


if __name__ == "__main__":
    import json

    result = create_hdri_dome("/path/to/environment.hdr", name="env_dome")
    print(json.dumps(result))
