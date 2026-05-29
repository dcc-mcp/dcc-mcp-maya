"""Generate a playblast preview of the current animation (issue #306).

Stage six: capture the active viewport across the playback range to an image
sequence or movie file so the workflow produces a reviewable artefact.
"""

from __future__ import annotations

import os
from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_FORMATS = ("qt", "avi", "image")


def create_playblast(
    output_path: str,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    width: int = 1280,
    height: int = 720,
    fmt: str = "image",
    show_ornaments: bool = False,
) -> dict:
    """Capture a playblast to ``output_path``.

    Args:
        output_path: Target file path (extension implied by ``fmt``).
        start_frame: First frame; defaults to the timeline minimum.
        end_frame: Last frame; defaults to the timeline maximum.
        width: Output width in pixels.
        height: Output height in pixels.
        fmt: ``image`` (frame sequence), ``qt`` (QuickTime), or ``avi``.
        show_ornaments: Keep HUD/ornaments in the capture.

    Returns:
        ToolResult dict with ``context.output_path``.
    """
    if fmt not in _FORMATS:
        return maya_error("Invalid fmt", "fmt must be one of {}".format(", ".join(_FORMATS)))
    if not output_path:
        return maya_error("Missing output_path", "output_path is required")

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )

    try:
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)

        if start_frame is None:
            start_frame = int(cmds.playbackOptions(query=True, minTime=True))
        if end_frame is None:
            end_frame = int(cmds.playbackOptions(query=True, maxTime=True))

        kwargs = {
            "filename": output_path,
            "startTime": start_frame,
            "endTime": end_frame,
            "width": width,
            "height": height,
            "showOrnaments": show_ornaments,
            "viewer": False,
            "forceOverwrite": True,
            "percent": 100,
        }
        if fmt == "image":
            kwargs["format"] = "image"
            kwargs["compression"] = "png"
        else:
            kwargs["format"] = fmt

        result_path = cmds.playblast(**kwargs)
        return maya_success(
            "Captured playblast to {}".format(result_path or output_path),
            prompt="Use export_scene_artifact to export the geometry alongside the preview.",
            output_path=result_path or output_path,
            start_frame=start_frame,
            end_frame=end_frame,
            fmt=fmt,
        )
    except Exception as exc:  # noqa: BLE001
        return maya_from_exception(exc, message="Failed to create playblast")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_playblast`."""
    return create_playblast(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
