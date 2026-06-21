"""Set up an Arnold HDR skydome environment for look-dev rendering."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import maya_warning


def setup_hdr_arnold(
    hdri_path: str,
    name: Optional[str] = None,
    intensity: float = 1.0,
    rotation: float = 0.0,
    visible_in_diffuse: bool = True,
    visible_in_specular: bool = True,
    set_renderer: bool = True,
    exposure: float = 0.0,
) -> dict:
    """Configure an Arnold HDR skydome environment light for look-dev.

    Creates an ``aiSkyDomeLight`` with an attached HDR file texture, switches the
    active renderer to Arnold (unless ``set_renderer=False``), and loads the
    MtoA plug-in if not already loaded.  Falls back to an ambient-light
    approximation when MtoA is unavailable, returning a warning rather than an error
    so callers can still render with Maya Software.

    Args:
        hdri_path: Absolute path to a ``.hdr``, ``.exr``, or ``.tx`` HDR image.
        name: Name for the skydome transform node.  Defaults to ``hdri_dome``.
        intensity: Light intensity multiplier.  Default: 1.0.
        rotation: Y-axis rotation in degrees for the HDRI orientation.  Default: 0.0.
        visible_in_diffuse: Enable diffuse contribution.  Default: True.
        visible_in_specular: Enable specular contribution.  Default: True.
        set_renderer: Switch ``defaultRenderGlobals.currentRenderer`` to ``arnold``
            when MtoA is available.  Default: True.
        exposure: Arnold ``exposure`` attribute on the dome light.  Default: 0.0.

    Returns:
        ToolResult with ``context.dome_node``, ``context.file_node``,
        ``context.hdri_path``, ``context.renderer_set``, ``context.mtoa_loaded``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Validate file path
        if not hdri_path:
            return skill_error(
                "hdri_path is required",
                "Provide an absolute path to a .hdr or .exr file.",
                possible_solutions=["Pass hdri_path='/path/to/environment.hdr'"],
                hdri_path=hdri_path,
            )

        node_name = name or "hdri_dome"

        # Attempt to load MtoA
        mtoa_loaded = False
        try:
            mtoa_loaded = bool(cmds.pluginInfo("mtoa", q=True, loaded=True))
            if not mtoa_loaded:
                cmds.loadPlugin("mtoa", quiet=True)
                mtoa_loaded = bool(cmds.pluginInfo("mtoa", q=True, loaded=True))
        except Exception:
            mtoa_loaded = False

        renderer_set = False
        dome_transform = None
        dome_shape = None
        file_node = None

        if mtoa_loaded:
            # Create Arnold aiSkyDomeLight
            dome_transform = cmds.createNode("transform", name=node_name)
            dome_shape = cmds.createNode("aiSkyDomeLight", name="{}_Shape".format(node_name), parent=dome_transform)
            cmds.setAttr("{}.intensity".format(dome_shape), intensity)
            cmds.setAttr("{}.rotateY".format(dome_transform), rotation)

            if cmds.attributeQuery("exposure", node=dome_shape, exists=True):
                cmds.setAttr("{}.exposure".format(dome_shape), exposure)

            # Connect HDR file texture
            file_node = cmds.createNode("file", name="{}_texture".format(node_name))
            cmds.setAttr("{}.fileTextureName".format(file_node), hdri_path, type="string")
            cmds.setAttr(
                "{}.colorSpace".format(file_node),
                "scene-linear Rec.709-sRGB",
                type="string",
            )
            color_port = "{}.color".format(dome_shape)
            out_color = "{}.outColor".format(file_node)
            cmds.connectAttr(out_color, color_port, force=True)

            if cmds.attributeQuery("aiDiffuse", node=dome_shape, exists=True):
                cmds.setAttr("{}.aiDiffuse".format(dome_shape), int(visible_in_diffuse))
            if cmds.attributeQuery("aiSpecular", node=dome_shape, exists=True):
                cmds.setAttr("{}.aiSpecular".format(dome_shape), int(visible_in_specular))

            # Switch renderer to Arnold
            if set_renderer:
                try:
                    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
                    renderer_set = True
                except Exception:
                    renderer_set = False

            return skill_success(
                "HDR skydome '{}' created from '{}'".format(dome_transform, hdri_path),
                prompt=(
                    "Call render_scene to render with this HDR environment. "
                    "Adjust intensity with set_light_rig_intensity or rotate_dome_y for orientation. "
                    "If exposure is too bright or dark, tweak the exposure parameter."
                ),
                dome_node=dome_transform,
                dome_shape=dome_shape,
                file_node=file_node,
                hdri_path=hdri_path,
                intensity=intensity,
                rotation=rotation,
                exposure=exposure,
                renderer_set=renderer_set,
                mtoa_loaded=mtoa_loaded,
            )
        else:
            # Fallback: ambient light approximation
            dome_transform = cmds.createNode("transform", name=node_name)
            dome_shape = cmds.createNode("ambientLight", name="{}_Shape".format(node_name), parent=dome_transform)
            cmds.setAttr("{}.intensity".format(dome_shape), intensity)
            file_node = cmds.createNode("file", name="{}_texture".format(node_name))
            cmds.setAttr("{}.fileTextureName".format(file_node), hdri_path, type="string")

            return maya_warning(
                "HDR dome '{}' created (Arnold fallback — MtoA unavailable)".format(dome_transform),
                warning="MtoA could not be loaded; used ambientLight as fallback.",
                prompt=(
                    "Install Arnold (MtoA) for full aiSkyDomeLight support. "
                    "Re-run setup_hdr_arnold after loading MtoA. "
                    "For now you can render with Maya Software renderer."
                ),
                dome_node=dome_transform,
                dome_shape=dome_shape,
                file_node=file_node,
                hdri_path=hdri_path,
                intensity=intensity,
                rotation=rotation,
                renderer_set=False,
                mtoa_loaded=False,
            )

    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to setup HDR Arnold environment")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`setup_hdr_arnold`."""
    return setup_hdr_arnold(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
