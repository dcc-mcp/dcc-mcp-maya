"""Bake full scene lighting to a texture using Maya's convertLightmap."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

logger = logging.getLogger(__name__)


def bake_lighting(
    objects: Optional[List[str]] = None,
    output_dir: str = "/tmp",
    resolution: int = 1024,
    samples: int = 4,
    file_format: str = "png",
    bake_shadows: bool = True,
) -> dict:
    """Bake diffuse + shadow lighting to a texture.

    Uses Maya's ``convertLightmap`` MEL procedure to bake scene lighting
    contributions to UV-unwrapped geometry.

    Args:
        objects: List of mesh names to bake.  If ``None``, the current selection
            is used.
        output_dir: Directory to write baked image files.  Default: ``"/tmp"``.
        resolution: Texture resolution in pixels (square).  Default: ``1024``.
        samples: Anti-aliasing sample count.  Default: ``4``.
        file_format: Image format (``"png"``, ``"tga"``, ``"exr"``).  Default: ``"png"``.
        bake_shadows: Include shadow contribution.  Default: ``True``.

    Returns:
        ToolResult dict with ``baked_files``, ``objects``, ``resolution``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or (cmds.ls(selection=True) or [])
        if not targets:
            return skill_error(
                "No objects specified",
                "Provide 'objects' or select meshes in Maya",
            )

        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as exc:
                return skill_error(
                    "Cannot create output directory: {}".format(output_dir),
                    str(exc),
                )

        baked_files = []
        for obj in targets:
            if not cmds.objExists(obj):
                logger.warning("Object not found, skipping: %s", obj)
                continue

            out_file = os.path.join(output_dir, "{}_lighting.{}".format(obj.replace(":", "_"), file_format))
            cmds.select(obj, replace=True)
            cmds.convertLightmap(
                camera="persp",
                resolution=resolution,
                samples=samples,
                shadows=bake_shadows,
                fileFormat=file_format,
                fileName=out_file,
            )
            baked_files.append(out_file)

        return skill_success(
            "Baked lighting for {} object(s)".format(len(baked_files)),
            prompt="Use bake_ambient_occlusion for AO or transfer_maps for normal maps.",
            baked_files=baked_files,
            objects=targets,
            resolution=resolution,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to bake lighting")


@skill_entry
def main(**kwargs):
    return bake_lighting(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
