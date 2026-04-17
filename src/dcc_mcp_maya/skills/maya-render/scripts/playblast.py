"""Capture a viewport playblast / screenshot."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import base64
import os
import tempfile
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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

        if frame is None:
            frame = cmds.currentTime(query=True)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="mcp_blast_") as tmp:
            tmp_base = tmp.name[:-4]  # strip .png — playblast appends frame number

        cmds.playblast(
            frame=[frame],
            format="image",
            compression="png",
            filename=tmp_base,
            width=width,
            height=height,
            percent=percent,
            viewer=False,
            showOrnaments=False,
            offScreen=True,
            forceOverwrite=True,
        )

        # Maya appends ".{frame}.png" → look for the file
        candidates = [
            "{}.{:04d}.png".format(tmp_base, int(frame)),
            "{}.{}.png".format(tmp_base, int(frame)),
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

        with open(img_path, "rb") as fh:
            img_bytes = fh.read()
        os.unlink(img_path)

        img_b64 = base64.b64encode(img_bytes).decode("ascii")

        return skill_success(
            "Viewport captured at frame {} ({}×{})".format(int(frame), width, height),
            prompt="Image captured. Use render_frame for final quality render.",
            image=img_b64,
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
