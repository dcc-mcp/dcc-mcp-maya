"""Generate a render farm submission manifest from current scene settings."""
from __future__ import annotations

import json
import os
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Generate a JSON manifest of current scene render settings for farm submission.

    Args:
        params: Dictionary with keys:
            - output_path (str): Where to save the manifest JSON. Required.
            - renderer (str): Renderer override. Default reads from scene.
            - chunk_size (int): Frames per task suggestion. Default 1.

    Returns:
        ActionResultModel with manifest path and summary.
    """
    output_path = params.get("output_path", "")
    renderer_override = params.get("renderer", "")
    chunk_size = int(params.get("chunk_size", 1))

    if not output_path:
        return error_result("Missing required parameter", "Parameter 'output_path' is required")

    try:
        scene_path = cmds.file(query=True, sceneName=True) or ""
        start_frame = int(cmds.playbackOptions(query=True, minTime=True))
        end_frame = int(cmds.playbackOptions(query=True, maxTime=True))

        # Detect renderer
        renderer = str(renderer_override) if renderer_override else ""
        if not renderer:
            render_globals = cmds.ls(type="renderGlobals")
            if render_globals:
                renderer = cmds.getAttr("{}.currentRenderer".format(render_globals[0]))
            else:
                renderer = "mayaSoftware"

        width = cmds.getAttr("defaultResolution.width")
        height = cmds.getAttr("defaultResolution.height")

        manifest = {
            "scene_path": scene_path,
            "maya_version": cmds.about(version=True),
            "renderer": renderer,
            "frame_range": {"start": start_frame, "end": end_frame},
            "chunk_size": chunk_size,
            "resolution": {"width": width, "height": height},
            "cameras": cmds.listCameras(perspective=True) or [],
        }

        output_path = str(output_path)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as fh:
            json.dump(manifest, fh, indent=2)

        total_frames = end_frame - start_frame + 1
        return success_result(
            "Generated submission manifest: {} frames, {}".format(total_frames, renderer),
            prompt="Use submit_deadline_job to submit this scene to the render farm.",
            manifest_path=output_path,
            frame_range="{}-{}".format(start_frame, end_frame),
            renderer=renderer,
            resolution="{}x{}".format(width, height),
        )
    except Exception as exc:
        return error_result("Failed to generate submission manifest", str(exc))
