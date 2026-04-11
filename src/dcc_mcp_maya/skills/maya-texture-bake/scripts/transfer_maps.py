"""Transfer normal/displacement/diffuse maps from high-res to low-res mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

_VALID_MAP_TYPES = {
    "normals",
    "displacement",
    "diffuse",
    "shading",
    "ambientOcclusion",
}


def transfer_maps(
    source: str,
    target: str,
    map_types: Optional[List[str]] = None,
    output_dir: str = "/tmp",
    resolution: int = 1024,
    file_format: str = "png",
    search_method: int = 0,
) -> dict:
    """Transfer texture maps from a high-res source to a low-res target mesh.

    Uses Maya's ``transferMaps`` command which samples the source mesh and
    writes image files for the target.

    Args:
        source: High-resolution (detail) mesh name.
        target: Low-resolution (game mesh) name to receive UV-mapped bakes.
        map_types: List of map type strings to transfer.  Supported:
            ``"normals"``, ``"displacement"``, ``"diffuse"``, ``"shading"``,
            ``"ambientOcclusion"``.  Default: ``["normals"]``.
        output_dir: Output directory for baked images.  Default: ``"/tmp"``.
        resolution: Output resolution in pixels (square).  Default: ``1024``.
        file_format: Image file format.  Default: ``"png"``.
        search_method: Surface sampling method (0 = closest point on surface).
            Default: ``0``.

    Returns:
        ActionResultModel dict with ``baked_files``, ``source``, ``target``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for node in (source, target):
            err = validate_node_exists(cmds, node)
            if err:
                return err

        bake_types = map_types or ["normals"]
        invalid = [t for t in bake_types if t not in _VALID_MAP_TYPES]
        if invalid:
            return skill_error(
                "Invalid map types: {}".format(invalid),
                "Valid types: {}".format(sorted(_VALID_MAP_TYPES)),
            )

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        baked_files = []
        for map_type in bake_types:
            out_file = os.path.join(
                output_dir,
                "{}_{}_from_{}.{}".format(target.replace(":", "_"), map_type, source.replace(":", "_"), file_format),
            )
            cmds.transferMaps(
                source,
                target,
                bakeMap=map_type,
                fileName=out_file,
                resolutionX=resolution,
                resolutionY=resolution,
                fileFormat=file_format,
                searchMethod=search_method,
            )
            baked_files.append(out_file)

        return skill_success(
            "Transferred {} map(s) from '{}' to '{}'".format(len(baked_files), source, target),
            prompt="Check output_dir for baked textures. Assign them to the target material.",
            baked_files=baked_files,
            source=source,
            target=target,
            resolution=resolution,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to transfer maps")


@skill_entry
def main(**kwargs):
    return transfer_maps(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
