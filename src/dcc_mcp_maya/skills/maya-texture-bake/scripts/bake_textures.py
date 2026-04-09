"""Bake lighting or texture to a UV map."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


def bake_textures(
    objects: List[str],
    file_path: str,
    resolution: int = 512,
    bake_type: str = "diffuse",
    renderer: str = "mentalRay",
    overscan: int = 3,
) -> dict:
    """Bake lighting or texture to a UV map.

    Args:
        objects: List of mesh objects to bake.
        file_path: Output texture file path (without extension).
        resolution: Output texture resolution in pixels.  Default: 512.
        bake_type: Bake type — ``"diffuse"``, ``"full_render"``,
            ``"normals"``, ``"ao"``.  Default: ``"diffuse"``.
        renderer: Renderer to use for baking — ``"mentalRay"`` or
            ``"arnold"``.  Default: ``"mentalRay"``.
        overscan: Anti-alias overscan in pixels.  Default: 3.

    Returns:
        ActionResultModel dict with ``context.baked_objects`` and
        ``context.file_path``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    valid_types = ("diffuse", "full_render", "normals", "ao")
    if bake_type not in valid_types:
        return error_result(
            "Invalid bake_type: {}".format(bake_type),
            "Use one of: {}".format(", ".join(valid_types)),
        ).to_dict()

    valid_renderers = ("mentalRay", "arnold")
    if renderer not in valid_renderers:
        return error_result(
            "Invalid renderer: {}".format(renderer),
            "Use one of: {}".format(", ".join(valid_renderers)),
        ).to_dict()

    if not objects:
        return error_result("No objects specified for baking", "objects list must not be empty").to_dict()

    if resolution < 1:
        return error_result(
            "Invalid resolution: {}".format(resolution),
            "Resolution must be >= 1",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return error_result("Objects not found: {}".format(", ".join(missing))).to_dict()

        bake_type_map = {
            "diffuse": "diffuse",
            "full_render": "fullRender",
            "normals": "normals",
            "ao": "occlusion",
        }
        internal_type = bake_type_map[bake_type]

        # Use Maya's convertSolidTx / bakeTextures for flexibility
        cmds.select(objects, replace=True)
        baked_files = []
        for obj in objects:
            out_path = "{}_{}".format(file_path, obj.replace("|", "_").replace(":", "_"))
            try:
                cmds.convertSolidTx(
                    obj,
                    fileImageName=out_path,
                    resolutionX=resolution,
                    resolutionY=resolution,
                    antiAlias=True,
                    bm=0,  # blend mode: normal
                    fts=True,  # fill texture seams
                    sp=False,  # do not show progress
                    backgroundMode=0,
                    renderSampler=internal_type,
                )
                baked_files.append(out_path)
            except Exception as bake_exc:
                logger.warning("Bake skipped for '%s': %s", obj, bake_exc)

        return success_result(
            "Baked {} object(s) to '{}'".format(len(baked_files), file_path),
            objects=objects,
            baked_count=len(baked_files),
            file_path=file_path,
            resolution=resolution,
            bake_type=bake_type,
            renderer=renderer,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("bake_textures failed")
        return error_result("Failed to bake textures", str(exc)).to_dict()


def main(**kwargs):
    return bake_textures(**kwargs)


if __name__ == "__main__":
    import json

    result = bake_textures()
    print(json.dumps(result))
