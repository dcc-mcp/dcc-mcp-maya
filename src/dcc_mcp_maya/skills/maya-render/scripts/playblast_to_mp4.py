"""Capture a viewport playblast sequence and encode it to MP4."""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_MAX_PLAYBLAST_DIM = 8192
_SAFE_PREFIX_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_prefix(prefix: str) -> str:
    value = _SAFE_PREFIX_RE.sub("_", str(prefix or "mcp_playblast")).strip("._")
    return value or "mcp_playblast"


def _clamp_dims(width: int, height: int) -> Tuple[int, int]:
    return max(1, min(int(width), _MAX_PLAYBLAST_DIM)), max(1, min(int(height), _MAX_PLAYBLAST_DIM))


def _frame_range(cmds, start_frame: Optional[float], end_frame: Optional[float]) -> Tuple[int, int]:
    if start_frame is None:
        try:
            start_frame = cmds.playbackOptions(query=True, minTime=True)
        except Exception:
            start_frame = cmds.currentTime(query=True)
    if end_frame is None:
        try:
            end_frame = cmds.playbackOptions(query=True, maxTime=True)
        except Exception:
            end_frame = start_frame
    f0 = int(round(float(start_frame)))
    f1 = int(round(float(end_frame)))
    if f1 < f0:
        f0, f1 = f1, f0
    return f0, f1


def _active_model_panel(cmds) -> Optional[str]:
    try:
        focused = cmds.getPanel(withFocus=True)
        if focused and cmds.getPanel(typeOf=focused) == "modelPanel":
            return str(focused)
    except Exception:
        pass
    try:
        panels = cmds.getPanel(type="modelPanel") or []
        visible = set(cmds.getPanel(visiblePanels=True) or [])
    except Exception:
        return None
    for panel in panels:
        if panel in visible:
            return str(panel)
    return str(panels[0]) if panels else None


def _viewport_renderer(cmds, panel: Optional[str]) -> Optional[str]:
    if not panel:
        return None
    try:
        return str(cmds.modelEditor(panel, query=True, rendererName=True))
    except Exception:
        return None


def _no_visible_panel(cmds) -> bool:
    try:
        panels = cmds.getPanel(type="modelPanel") or []
        visible = cmds.getPanel(visiblePanels=True) or []
        return not any(panel in visible for panel in panels)
    except Exception:
        return False


def _sequence_files(prefix_path: str, compression: str) -> List[str]:
    suffix = "." + compression.lower().lstrip(".")
    files = glob.glob(prefix_path + ".*" + suffix)
    direct = prefix_path + suffix
    if os.path.exists(direct):
        files.append(direct)
    return sorted(set(files))


def _nonempty_sequence_or_error(files: List[str]) -> Optional[dict]:
    if not files:
        return skill_error(
            "Playblast sequence files not found",
            "Could not locate image files produced by Maya playblast.",
        )
    empty = [path for path in files if os.path.exists(path) and os.path.getsize(path) == 0]
    if empty:
        return skill_error(
            "Playblast sequence produced empty image file(s)",
            "Maya playblast wrote one or more 0-byte image files.",
            error_code="EMPTY_PLAYBLAST_SEQUENCE",
            empty_files=empty,
            possible_solutions=[
                "Use maya_render__render_frame for preview frames when Maya is minimized or playblast is unavailable.",
                "Bring Maya to the foreground and ensure a model panel is visible before recording viewport previews.",
            ],
        )
    return None


def _encode_mp4(
    ffmpeg: str, input_pattern: str, output_path: str, fps: int, overwrite: bool
) -> subprocess.CompletedProcess:
    command = [
        ffmpeg,
        "-y" if overwrite else "-n",
        "-framerate",
        str(fps),
        "-i",
        input_pattern,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        output_path,
    ]
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def playblast_to_mp4(
    output_dir: Optional[str] = None,
    prefix: str = "mcp_playblast",
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
    width: int = 1920,
    height: int = 1080,
    percent: int = 100,
    fps: int = 24,
    off_screen: Optional[bool] = None,
    show_ornaments: bool = False,
    output_path: Optional[str] = None,
    keep_frames: bool = False,
    overwrite: bool = True,
) -> dict:
    """Record a viewport playblast image sequence and encode it to MP4."""

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return skill_error(
                "ffmpeg not found",
                "playblast_to_mp4 requires ffmpeg on PATH to encode the image sequence.",
                possible_solutions=[
                    "Install ffmpeg and ensure it is available on PATH.",
                    "Use capture_playblast_sequence when only image frames are needed.",
                ],
            )

        created_temp_dir = False
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="dcc_mcp_maya_playblast_mp4_")
            created_temp_dir = True
        out_dir = Path(os.path.expandvars(os.path.expanduser(str(output_dir))))
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_prefix = _safe_prefix(prefix)
        prefix_path = str(out_dir / safe_prefix)
        if output_path is None:
            output_path = str(out_dir / "{}.mp4".format(safe_prefix))
        else:
            output_path = str(Path(os.path.expandvars(os.path.expanduser(str(output_path)))))
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        width, height = _clamp_dims(width, height)
        percent = max(1, min(int(percent), 100))
        fps = max(1, min(int(fps), 240))
        f0, f1 = _frame_range(cmds, start_frame, end_frame)
        panel = _active_model_panel(cmds)
        viewport_renderer = _viewport_renderer(cmds, panel)
        if off_screen is None:
            off_screen = bool(cmds.about(batch=True)) or _no_visible_panel(cmds)

        playblast_kwargs = dict(
            startTime=f0,
            endTime=f1,
            format="image",
            compression="png",
            filename=prefix_path,
            width=width,
            height=height,
            percent=percent,
            viewer=False,
            showOrnaments=bool(show_ornaments),
            offScreen=bool(off_screen),
            forceOverwrite=True,
        )
        if panel:
            playblast_kwargs["editorPanelName"] = panel
        cmds.playblast(**playblast_kwargs)

        files = _sequence_files(prefix_path, "png")
        empty_error = _nonempty_sequence_or_error(files)
        if empty_error:
            empty_error["context"].update(
                {
                    "output_dir": str(out_dir),
                    "prefix": safe_prefix,
                    "panel": panel,
                    "viewport_renderer": viewport_renderer,
                    "off_screen": bool(off_screen),
                }
            )
            return empty_error

        input_pattern = "{}.%04d.png".format(prefix_path)
        proc = _encode_mp4(ffmpeg, input_pattern, output_path, fps, bool(overwrite))
        if proc.returncode != 0:
            return skill_error(
                "ffmpeg failed to encode MP4",
                proc.stderr.strip() or proc.stdout.strip() or "ffmpeg exited with a non-zero status.",
                output_path=output_path,
                input_pattern=input_pattern,
                exit_code=proc.returncode,
            )
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            return skill_error(
                "MP4 output is empty",
                "ffmpeg completed but did not produce a non-empty MP4 file.",
                output_path=output_path,
                input_pattern=input_pattern,
            )

        if not keep_frames:
            for path in files:
                try:
                    os.unlink(path)
                except OSError:
                    pass

        return skill_success(
            "Captured viewport MP4: {}".format(output_path),
            output_path=output_path,
            output_size=os.path.getsize(output_path),
            frame_files=files if keep_frames else [],
            kept_frames=bool(keep_frames),
            frame_count=len(files),
            start_frame=f0,
            end_frame=f1,
            width=width,
            height=height,
            percent=percent,
            fps=fps,
            panel=panel,
            viewport_renderer=viewport_renderer,
            off_screen=bool(off_screen),
            show_ornaments=bool(show_ornaments),
            created_temp_dir=created_temp_dir,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to capture viewport MP4")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`playblast_to_mp4`."""
    return playblast_to_mp4(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
