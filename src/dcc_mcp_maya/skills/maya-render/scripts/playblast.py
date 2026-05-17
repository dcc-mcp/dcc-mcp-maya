"""Capture a viewport playblast / screenshot."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import base64
import os
import tempfile
from typing import Optional, Tuple

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_MAX_PLAYBLAST_DIM = 8192


def _clamp_playblast_dims(width: int, height: int) -> Tuple[int, int]:
    w = max(1, min(int(width), _MAX_PLAYBLAST_DIM))
    h = max(1, min(int(height), _MAX_PLAYBLAST_DIM))
    return w, h


def _playblast_frame_range(frame: float) -> Tuple[int, int]:
    fnum = int(round(float(frame)))
    return (fnum, fnum)


def _read_nonempty_png(path: str) -> bytes:
    with open(path, "rb") as fh:
        img_bytes = fh.read()
    if not img_bytes:
        raise ValueError("EMPTY_PLAYBLAST")
    return img_bytes


def playblast(
    width: int = 1920,
    height: int = 1080,
    frame: Optional[float] = None,
    percent: int = 100,
) -> dict:
    """Capture a viewport screenshot using Maya playblast.

    Returns the image as a base64-encoded PNG string so it can be inspected
    by an AI agent without writing to permanent storage.

    Args:
        width: Output width in pixels.
        height: Output height in pixels.
        frame: Frame number to capture.  If None, the current frame is used.
        percent: Resolution percentage (1–100).

    Returns:
        ToolResult dict with ``context.image`` (base64 PNG) and
        ``context.frame``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        img_path: Optional[str] = None
        if frame is None:
            frame = cmds.currentTime(query=True)

        width, height = _clamp_playblast_dims(width, height)
        percent = max(1, min(int(percent), 100))
        f0, f1 = _playblast_frame_range(frame)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="mcp_blast_") as tmp:
            tmp_base = tmp.name[:-4]  # strip .png — playblast appends frame number

        cmds.playblast(
            frame=(f0, f1),
            format="image",
            compression="png",
            filename=tmp_base,
            width=width,
            height=height,
            percent=percent,
            viewer=False,
            showOrnaments=False,
            offScreen=True,
        )

        # Maya appends ".{frame}.png" → look for the file
        candidates = [
            "{}.{:04d}.png".format(tmp_base, f0),
            "{}.{}.png".format(tmp_base, f0),
            "{}.png".format(tmp_base),
        ]
        img_path = None
        for c in candidates:
            if os.path.exists(c):
                img_path = c
                break

        if img_path is None:
            return skill_error(
                "Playblast file not found",
                "Could not locate output PNG from playblast",
            )

        img_bytes = _read_nonempty_png(img_path)
        os.unlink(img_path)

        img_b64 = base64.b64encode(img_bytes).decode("ascii")

        return skill_success(
            "Viewport captured at frame {} ({}×{})".format(f0, width, height),
            prompt="Image captured. For framing before capture, use capture_viewport with view_fit=True.",
            image=img_b64,
            frame=frame,
            width=width,
            height=height,
        )
    except ValueError as exc:
        if str(exc) != "EMPTY_PLAYBLAST":
            raise
        try:
            if img_path and os.path.exists(img_path):
                os.unlink(img_path)
        except OSError:
            pass
        return skill_error(
            "Playblast produced an empty image",
            "Maya playblast wrote a 0-byte PNG",
            possible_solutions=[
                "Retry after ensuring a model panel exists.",
                "Use capture_viewport with off_screen=True and view_fit=True for hidden or minimized Maya sessions.",
            ],
            error_code="EMPTY_PLAYBLAST",
            frame=frame,
            width=width,
            height=height,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Playblast failed")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`playblast`."""
    return playblast(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
