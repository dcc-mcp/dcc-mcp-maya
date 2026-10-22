"""Bake lighting or texture to a UV map."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes

logger = logging.getLogger(__name__)


def bake_textures(
    objects: List[str],
    file_path: str,
    resolution: int = 512,
    bake_type: str = "diffuse",
    renderer: str = "arnold",
    overscan: int = 3,
) -> dict:
    """Bake texture maps using the existing convertSolidTx backend, not Arnold RTT.

    Args:
        objects: List of mesh objects to bake.
        file_path: Output texture file path (without extension).
        resolution: Output texture resolution in pixels.  Default: 512.
        bake_type: Bake type — ``"diffuse"``, ``"full_render"``,
            ``"normals"``, ``"ao"``.  Default: ``"diffuse"``.
        renderer: Renderer to use for baking. Maya 2017 and later use
            Arnold; the removed mentalRay renderer is rejected. Default:
            ``"arnold"``.
        overscan: Anti-alias overscan in pixels.  Default: 3.

    Returns:
        Success only if every object produced non-empty files. Failures retain
        verified ``baked_files`` and per-object errors; ``partial`` marks retained
        outputs. Renderer and selection are restored before returning.
    """

    valid_types = ("diffuse", "full_render", "normals", "ao")
    if bake_type not in valid_types:
        return skill_error(
            "Invalid bake_type: {}".format(bake_type),
            "Use one of: {}".format(", ".join(valid_types)),
        )

    valid_renderers = ("arnold",)
    if renderer not in valid_renderers:
        return skill_error(
            "Invalid renderer: {}".format(renderer),
            "Use one of: {}".format(", ".join(valid_renderers)),
        )

    if not objects:
        return skill_error("No objects specified for baking", "objects list must not be empty")

    if resolution < 1:
        return skill_error(
            "Invalid resolution: {}".format(resolution),
            "Resolution must be >= 1",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, list(objects))
        if err:
            return err

        renderer_attr = "defaultRenderGlobals.currentRenderer"
        original_renderer = cmds.getAttr(renderer_attr)
        original_selection = cmds.ls(selection=True, long=True) or []
        try:
            cmds.setAttr(renderer_attr, renderer, type="string")
            active_renderer = cmds.getAttr(renderer_attr)
            if active_renderer != renderer:
                return skill_error(
                    "Could not activate renderer: {}".format(renderer),
                    "Maya reports the active renderer as {!r}.".format(active_renderer),
                )

            bake_type_map = {
                "diffuse": "diffuse",
                "full_render": "fullRender",
                "normals": "normals",
                "ao": "occlusion",
            }
            internal_type = bake_type_map[bake_type]

            # shortcut: Legacy convertSolidTx flags remain; replace with verified Arnold RTT for full bake support.
            cmds.select(objects, replace=True)
            baked_files = []
            baked_objects = []
            failed_objects = []
            for obj in objects:
                out_path = "{}_{}".format(file_path, obj.replace("|", "_").replace(":", "_"))
                try:
                    file_nodes = cmds.convertSolidTx(
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
                    if isinstance(file_nodes, str):
                        file_nodes = [file_nodes]
                    if not file_nodes:
                        raise ValueError("Conversion returned no file texture nodes")
                    for node in file_nodes:
                        output = cmds.getAttr("{}.fileTextureName".format(node))
                        if not output:
                            raise ValueError("Conversion returned an empty texture path")
                        if not os.path.isabs(output):
                            output = cmds.workspace(expandName=output)
                        if not os.path.isfile(output) or os.path.getsize(output) == 0:
                            raise ValueError("Missing or empty baked texture: {}".format(output))
                        baked_files.append(output)
                    baked_objects.append(obj)
                except Exception as bake_exc:
                    logger.warning("Bake skipped for '%s': %s", obj, bake_exc)
                    failed_objects.append({"object": obj, "error": str(bake_exc)})

            context = {
                "objects": objects,
                "baked_count": len(baked_objects),
                "baked_objects": baked_objects,
                "baked_files": baked_files,
                "failed_objects": failed_objects,
                "partial": bool(failed_objects and baked_files),
                "file_path": file_path,
                "resolution": resolution,
                "bake_type": bake_type,
                "renderer": renderer,
            }
            if failed_objects:
                return skill_error(
                    "Baking failed for {} of {} object(s)".format(len(failed_objects), len(objects)),
                    "Inspect failed_objects before retrying; successful outputs are retained.",
                    **context,
                )
            return skill_success(
                "Baked {} object(s) to '{}'".format(len(baked_objects), file_path),
                prompt="Check the result with list_texture_bake or use related actions to continue.",
                **context,
            )
        finally:
            try:
                cmds.setAttr(renderer_attr, original_renderer, type="string")
            finally:
                if original_selection:
                    cmds.select(original_selection, replace=True)
                else:
                    cmds.select(clear=True)
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake textures")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bake_textures`."""
    return bake_textures(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
