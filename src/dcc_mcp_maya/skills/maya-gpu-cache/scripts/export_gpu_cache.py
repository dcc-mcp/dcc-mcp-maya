"""Export selected or specified objects to GPU cache (.abc) for fast viewport display."""
from __future__ import annotations

import os
from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Export objects to GPU cache format.

    GPU cache is an Alembic-based format optimised for Maya viewport display.
    Requires the 'gpuCache' plugin to be loaded.

    Args:
        params: Dictionary containing:
            - objects (list[str]): Object names to export. Required.
            - output_dir (str): Output directory path. Required.
            - filename (str): Base filename without extension. Default 'gpu_cache'.
            - start_frame (int): Start frame. Default current frame.
            - end_frame (int): End frame. Default current frame.
            - optimize (bool): Run optimize command before export. Default True.
            - all_dagobjects (bool): Export all DAG objects. Overrides 'objects'. Default False.

    Returns:
        ActionResultModel with export path.
    """
    objects: List[str] = list(params.get("objects", []))  # type: ignore[arg-type]
    output_dir = str(params.get("output_dir", ""))
    filename = str(params.get("filename", "gpu_cache"))
    current_frame = int(cmds.currentTime(query=True))
    start_frame = int(params.get("start_frame", current_frame))
    end_frame = int(params.get("end_frame", current_frame))
    optimize = bool(params.get("optimize", True))
    all_dag = bool(params.get("all_dagobjects", False))

    if not output_dir:
        return error_result("Invalid parameters", "'output_dir' is required.")
    if not all_dag and not objects:
        return error_result(
            "Invalid parameters",
            "Either 'objects' or 'all_dagobjects=true' is required.",
        )

    try:
        # Ensure plugin loaded
        if not cmds.pluginInfo("gpuCache", query=True, loaded=True):
            cmds.loadPlugin("gpuCache")

        os.makedirs(output_dir, exist_ok=True)

        if optimize:
            cmds.GPUCacheExportAll  # noqa: B018 — just access to avoid unused import warning

        kwargs: Dict[str, object] = {
            "startTime": start_frame,
            "endTime": end_frame,
            "optimize": optimize,
            "optimizationThreshold": 40000,
            "writeMaterials": True,
            "useBaseTessellation": True,
            "directory": output_dir,
            "fileName": filename,
        }

        if all_dag:
            kwargs["allDagObjects"] = True
            cmds.gpuCache(**kwargs)
        else:
            cmds.select(objects, replace=True)
            kwargs["selection"] = True
            cmds.gpuCache(**kwargs)

        output_path = os.path.join(output_dir, "{}.abc".format(filename))
        return success_result(
            "Exported GPU cache to '{}'".format(output_path),
            prompt="Use import_gpu_cache to load this cache into another scene.",
            output_path=output_path,
            start_frame=start_frame,
            end_frame=end_frame,
        )
    except Exception as exc:
        return error_result("Failed to export GPU cache", str(exc))
