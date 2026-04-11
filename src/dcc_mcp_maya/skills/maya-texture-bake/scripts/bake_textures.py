"""Bake lighting or texture to a UV map."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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

    valid_types = ("diffuse", "full_render", "normals", "ao")
    if bake_type not in valid_types:
        return maya_error(
            "Invalid bake_type: {}".format(bake_type),
            "Use one of: {}".format(", ".join(valid_types)),
        )

    valid_renderers = ("mentalRay", "arnold")
    if renderer not in valid_renderers:
        return maya_error(
            "Invalid renderer: {}".format(renderer),
            "Use one of: {}".format(", ".join(valid_renderers)),
        )

    if not objects:
        return maya_error("No objects specified for baking", "objects list must not be empty")

    if resolution < 1:
        return maya_error(
            "Invalid resolution: {}".format(resolution),
            "Resolution must be >= 1",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return maya_error("Objects not found: {}".format(", ".join(missing)))

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

        return maya_success(
            "Baked {} object(s) to '{}'".format(len(baked_files), file_path),
            objects=objects,
            baked_count=len(baked_files),
            file_path=file_path,
            resolution=resolution,
            bake_type=bake_type,
            renderer=renderer,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to bake textures")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_textures`."""
    return bake_textures(**kwargs)

if __name__ == "__main__":
    import json

    result = bake_textures()
    print(json.dumps(result))
