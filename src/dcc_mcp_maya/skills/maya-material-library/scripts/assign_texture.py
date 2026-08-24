"""Bind one typed texture map to an Arnold material slot."""

from __future__ import annotations

import re
from pathlib import Path

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._texture_paths import MAX_TEXTURE_PATH_LENGTH, resolve_texture_path

_ARNOLD_SLOTS = {
    "base_color": ("baseColor", "outColor", "sRGB", False),
    "normal": ("normalCamera", "outColor", "Raw", False),
    "roughness": ("specularRoughness", "outAlpha", "Raw", True),
}
_PLACEMENT_CONNECTIONS = (
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
    ("outUV", "uvCoord"),
    ("outUvFilterSize", "uvFilterSize"),
)


def _node_stem(material_name: str, slot: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", "{}_{}".format(material_name, slot)).strip("_")
    return value[:120] or "texture"


def assign_texture(
    material_name: str,
    texture_path: str,
    slot: str,
    color_space: str = "auto",
    udim_mode: str = "off",
) -> dict:
    """Create and verify one file/place2d network for a typed Arnold slot."""

    created = []
    cmds = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not isinstance(material_name, str) or not material_name.strip() or len(material_name) > 512:
            return skill_error("Invalid material", "material_name must be a non-empty Maya node name")
        if slot not in _ARNOLD_SLOTS:
            return skill_error(
                "Unsupported texture slot",
                "slot must be one of: {}".format(", ".join(sorted(_ARNOLD_SLOTS))),
            )
        if color_space not in {"auto", "sRGB", "Raw"}:
            return skill_error("Unsupported color space", "color_space must be auto, sRGB, or Raw")
        if udim_mode not in {"off", "udim"}:
            return skill_error("Unsupported UDIM mode", "udim_mode must be off or udim")
        if not isinstance(texture_path, str) or not texture_path.strip() or len(texture_path) > MAX_TEXTURE_PATH_LENGTH:
            return skill_error("Invalid texture path", "texture_path must be a non-empty bounded path")

        try:
            path, tile_count = resolve_texture_path(texture_path, udim_mode)
        except ValueError as exc:
            return skill_error("Texture file was not found", str(exc), path=texture_path)
        if not cmds.objExists(material_name):
            return skill_error("Material was not found", "No Maya node exists with that name", material=material_name)
        material_type = str(cmds.nodeType(material_name))
        if material_type != "aiStandardSurface":
            return skill_error(
                "Unsupported material type",
                "base_color binding currently requires aiStandardSurface",
                material=material_name,
                material_type=material_type,
            )

        destination_attr, source_attr, automatic_color_space, alpha_is_luminance = _ARNOLD_SLOTS[slot]
        destination = "{}.{}".format(material_name, destination_attr)
        existing = list(cmds.listConnections(destination, source=True, destination=False, plugs=True) or [])
        if existing:
            return skill_error(
                "Material slot is already connected",
                "Disconnect or explicitly migrate the existing network before assigning a texture.",
                material=material_name,
                slot=slot,
                existing_sources=existing[:16],
            )

        stem = _node_stem(material_name, slot)
        texture_node = cmds.shadingNode("file", asTexture=True, name="{}_file".format(stem))
        created.append(texture_node)
        place_node = cmds.shadingNode("place2dTexture", asUtility=True, name="{}_place2d".format(stem))
        created.append(place_node)
        for placement_source_attr, placement_destination_attr in _PLACEMENT_CONNECTIONS:
            cmds.connectAttr(
                "{}.{}".format(place_node, placement_source_attr),
                "{}.{}".format(texture_node, placement_destination_attr),
                force=True,
            )

        resolved_color_space = automatic_color_space if color_space == "auto" else color_space
        cmds.setAttr("{}.fileTextureName".format(texture_node), str(path), type="string")
        cmds.setAttr("{}.colorSpace".format(texture_node), resolved_color_space, type="string")
        tiling_mode = 3 if udim_mode == "udim" else 0
        cmds.setAttr("{}.uvTilingMode".format(texture_node), tiling_mode)
        if alpha_is_luminance:
            cmds.setAttr("{}.alphaIsLuminance".format(texture_node), True)
        utility_node = None
        utility_input_source = None
        if slot == "normal":
            utility_node = cmds.createNode("aiNormalMap", name="{}_normal".format(stem))
            created.append(utility_node)
            utility_input_source = "{}.outColor".format(texture_node)
            cmds.connectAttr(utility_input_source, "{}.input".format(utility_node), force=False)
            source = "{}.outValue".format(utility_node)
        else:
            source = "{}.{}".format(texture_node, source_attr)
        cmds.connectAttr(source, destination, force=False)

        actual_path = str(cmds.getAttr("{}.fileTextureName".format(texture_node)))
        actual_color_space = str(cmds.getAttr("{}.colorSpace".format(texture_node)))
        actual_tiling = cmds.getAttr("{}.uvTilingMode".format(texture_node))
        actual_alpha_is_luminance = (
            bool(cmds.getAttr("{}.alphaIsLuminance".format(texture_node))) if alpha_is_luminance else False
        )
        if (
            Path(actual_path).resolve() != path
            or actual_color_space != resolved_color_space
            or actual_tiling != tiling_mode
            or actual_alpha_is_luminance != alpha_is_luminance
            or (
                utility_node is not None and not cmds.isConnected(utility_input_source, "{}.input".format(utility_node))
            )
            or not cmds.isConnected(source, destination)
        ):
            cmds.delete(created)
            return skill_error(
                "Texture binding did not round-trip",
                "Native Maya readback differs from the requested texture network.",
                material=material_name,
                slot=slot,
            )

        return skill_success(
            "Bound {} texture to '{}'".format(slot, material_name),
            material=material_name,
            material_type=material_type,
            slot=slot,
            destination_attr=destination,
            texture_node=texture_node,
            place2d_node=place_node,
            utility_node=utility_node,
            texture_path=actual_path,
            color_space=actual_color_space,
            udim_mode=udim_mode,
            tile_count=tile_count,
            verified=True,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        if cmds is not None and created:
            try:
                cmds.delete(created)
            except Exception:
                pass
        return skill_exception(exc, message="Failed to assign texture")


@skill_entry
def main(**kwargs) -> dict:
    return assign_texture(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
