"""Export selected objects to a GPU cache (.abc) file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


def export_gpu_cache(
    objects: List[str],
    file_path: str,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    optimize: bool = True,
    write_material_color: bool = True,
) -> dict:
    """Export objects to a GPU cache Alembic file.

    Args:
        objects: List of transform/mesh names to export.
        file_path: Output ``.abc`` file path.  The directory must exist.
        start_frame: Export range start.  Defaults to playback start.
        end_frame: Export range end.  Defaults to playback end.
        optimize: If ``True``, enable gpuCache optimisation for faster playback.
        write_material_color: Write diffuse color metadata.

    Returns:
        ActionResultModel dict with ``context.file_path`` and ``context.objects``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        # Ensure plugin loaded
        if not cmds.pluginInfo("gpuCache", query=True, loaded=True):
            cmds.loadPlugin("gpuCache")

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Objects not found",
                "Missing: {}".format(", ".join(missing)),
            ).to_dict()

        out_dir = os.path.dirname(os.path.abspath(file_path))
        out_name = os.path.splitext(os.path.basename(file_path))[0]

        if not os.path.isdir(out_dir):
            return error_result(
                "Output directory does not exist: {}".format(out_dir),
                "Create the directory first.",
            ).to_dict()

        s = start_frame if start_frame is not None else cmds.playbackOptions(query=True, min=True)
        e = end_frame if end_frame is not None else cmds.playbackOptions(query=True, max=True)

        cmds.select(objects, replace=True)
        cmds.gpuCache(
            objects,
            startTime=s,
            endTime=e,
            optimize=optimize,
            writeMaterials=write_material_color,
            dataFormat="ogawa",
            directory=out_dir,
            fileName=out_name,
        )

        return success_result(
            "Exported GPU cache to '{}'".format(file_path),
            prompt="Use import_gpu_cache to reload the file, or list_gpu_caches to verify.",
            file_path=file_path,
            objects=objects,
            frame_range=[s, e],
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("export_gpu_cache failed")
        return error_result("Failed to export GPU cache", str(exc)).to_dict()


def main(**kwargs):
    return export_gpu_cache(**kwargs)


if __name__ == "__main__":
    import json

    result = export_gpu_cache(["pSphere1"], "/tmp/test_cache.abc")
    print(json.dumps(result, indent=2))
