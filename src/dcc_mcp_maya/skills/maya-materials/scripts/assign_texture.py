"""Bind a file texture to a named material slot with verified connections."""

from __future__ import annotations

import os
from typing import Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

_SLOT_ALIASES = {
    "base_color": ("baseColor", "color"),
    "basecolor": ("baseColor", "color"),
    "color": ("color", "baseColor"),
    "roughness": ("specularRoughness", "roughness"),
    "normal": ("normalCamera", "normal"),
    "bump": ("normalCamera", "bump"),
}
_RAW_SLOTS = {"roughness", "metalness", "metallic", "normal", "bump"}


def _first_existing(cmds, material_name: str, candidates):
    for candidate in candidates:
        try:
            if cmds.objExists("{}.{}".format(material_name, candidate)):
                return candidate
        except Exception:
            continue
    return None


def _connect_place2d(cmds, place_node: str, file_node: str) -> None:
    for source, target in (
        ("coverage", "coverage"),
        ("translateFrame", "translateFrame"),
        ("rotateFrame", "rotateFrame"),
        ("mirrorU", "mirrorU"),
        ("mirrorV", "mirrorV"),
        ("stagger", "stagger"),
        ("wrapU", "wrapU"),
        ("wrapV", "wrapV"),
        ("repeatUV", "repeatUV"),
        ("offset", "offset"),
        ("rotateUV", "rotateUV"),
        ("noiseUV", "noiseUV"),
        ("vertexUvOne", "vertexUvOne"),
        ("vertexUvTwo", "vertexUvTwo"),
        ("vertexUvThree", "vertexUvThree"),
        ("vertexCameraOne", "vertexCameraOne"),
    ):
        try:
            cmds.connectAttr("{}.{}".format(place_node, source), "{}.{}".format(file_node, target), force=True)
        except Exception:
            pass


def assign_texture(
    material_name: str,
    texture_path: str,
    slot: str = "base_color",
    color_space: Optional[str] = None,
    use_udim: bool = False,
    file_node_name: Optional[str] = None,
) -> dict:
    """Create a file texture network and connect it to ``material_name``.

    ``slot`` accepts ``base_color``, ``roughness``, ``metalness`` and ``normal``.
    Scalar slots use ``outAlpha``; normal maps use a ``bump2d`` conversion node.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, material_name)
        if err:
            return err
        if not texture_path:
            return skill_error("texture_path is required", "Provide an absolute or project-relative texture path.")

        slot_key = str(slot or "base_color").strip().lower()
        candidates = _SLOT_ALIASES.get(slot_key, (slot,))
        material_attr = _first_existing(cmds, material_name, candidates)
        if not material_attr:
            return skill_error(
                "Material slot '{}' is unavailable".format(slot),
                "The material does not expose a compatible attribute for this slot.",
                material_name=material_name,
                slot=slot,
                candidates=list(candidates),
            )

        stem = file_node_name or "{}_{}_file".format(material_name, slot_key)
        file_node = cmds.shadingNode("file", asTexture=True, name=stem)
        place_node = cmds.shadingNode("place2dTexture", asUtility=True, name="{}_place2d".format(stem))
        cmds.setAttr("{}.fileTextureName".format(file_node), os.fspath(texture_path), type="string")
        if use_udim:
            cmds.setAttr("{}.uvTilingMode".format(file_node), 3)
        resolved_color_space = color_space or ("Raw" if slot_key in _RAW_SLOTS else "sRGB")
        if cmds.objExists("{}.colorSpace".format(file_node)):
            cmds.setAttr("{}.colorSpace".format(file_node), resolved_color_space, type="string")
        _connect_place2d(cmds, place_node, file_node)

        source_plug = "{}.outColor".format(file_node)
        conversion_node = None
        if slot_key in {"normal", "bump"}:
            conversion_node = cmds.shadingNode("bump2d", asUtility=True, name="{}_bump2d".format(stem))
            cmds.setAttr("{}.bumpInterp".format(conversion_node), 1)
            cmds.connectAttr("{}.outAlpha".format(file_node), "{}.bumpValue".format(conversion_node), force=True)
            source_plug = "{}.outNormal".format(conversion_node)
        elif slot_key in _RAW_SLOTS:
            source_plug = "{}.outAlpha".format(file_node)
        destination_plug = "{}.{}".format(material_name, material_attr)
        cmds.connectAttr(source_plug, destination_plug, force=True)

        verified = False
        try:
            verified = bool(cmds.isConnected(source_plug, destination_plug))
        except Exception:
            verified = bool(cmds.listConnections(destination_plug, source=True, plugs=True))
        if not verified:
            return skill_error(
                "Texture connection could not be verified",
                "Maya did not report the requested source connected to the material slot.",
                material_name=material_name,
                slot=slot,
                file_node=file_node,
                destination=destination_plug,
            )
        return skill_success(
            "Assigned '{}' texture to {}.{}".format(texture_path, material_name, material_attr),
            material_name=material_name,
            slot=slot_key,
            material_attribute=material_attr,
            texture_path=os.fspath(texture_path),
            file_node=file_node,
            place2d_node=place_node,
            conversion_node=conversion_node,
            color_space=resolved_color_space,
            use_udim=bool(use_udim),
            source_plug=source_plug,
            destination_plug=destination_plug,
            verified=True,
            prompt="Use get_material_connections to inspect the texture network or render_frame to preview it.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to assign texture")


@skill_entry
def main(**kwargs) -> dict:
    return assign_texture(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
