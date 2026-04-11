"""Export selected objects to a GPU cache (.abc) file."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Ensure plugin loaded
        if not cmds.pluginInfo("gpuCache", query=True, loaded=True):
            cmds.loadPlugin("gpuCache")

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return maya_error(
                "Objects not found",
                "Missing: {}".format(", ".join(missing)),
            )

        out_dir = os.path.dirname(os.path.abspath(file_path))
        out_name = os.path.splitext(os.path.basename(file_path))[0]

        if not os.path.isdir(out_dir):
            return maya_error(
                "Output directory does not exist: {}".format(out_dir),
                "Create the directory first.",
            )

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

        return maya_success(
            "Exported GPU cache to '{}'".format(file_path),
            prompt="Use import_gpu_cache to reload the file, or list_gpu_caches to verify.",
            file_path=file_path,
            objects=objects,
            frame_range=[s, e],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to export GPU cache")


def main(**kwargs):
    return export_gpu_cache(**kwargs)


if __name__ == "__main__":
    import json

    result = export_gpu_cache(["pSphere1"], "/tmp/test_cache.abc")
    print(json.dumps(result, indent=2))
