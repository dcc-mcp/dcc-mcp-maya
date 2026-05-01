"""Capture the Maya viewport as a PNG image (base64-encoded)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import base64
import os
import tempfile
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def capture_viewport(
    width: int = 1920,
    height: int = 1080,
    frame: Optional[float] = None,
    off_screen: Optional[bool] = None,
) -> dict:
    """Capture the Maya viewport as a PNG image (base64-encoded).

    Uses ``cmds.playblast`` to render the active viewport into a temporary
    PNG file and returns the image bytes as a Base64 string.  Unlike the
    OS-level ``diagnostics__screenshot`` tool, playblast renders directly
    from Maya's render context and works even when the Maya window is
    minimized, hidden behind another window, or running in batch mode
    (issue #152).

    Args:
        width: Image width in pixels.  Default: 1920.
        height: Image height in pixels.  Default: 1080.
        frame: Frame to capture.  Defaults to the current frame.
        off_screen: When ``True`` (or when running in batch mode / no
            visible Maya window) render off-screen via Maya's offscreen
            framebuffer.  Default: auto-detect.

    Returns:
        ToolResult dict with ``context.image`` (base64 PNG string).
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")

    try:
        if frame is None:
            frame = cmds.currentTime(query=True)

        # Auto-enable off-screen rendering when Maya is running in batch
        # mode (mayapy) or when no model panel is currently focusable —
        # both are situations where on-screen capture would silently
        # produce a black frame or raise (issue #152).
        if off_screen is None:
            off_screen = bool(cmds.about(batch=True)) or _no_visible_panel(cmds)

        # playblast writes  <prefix>.<frame_padded>.png
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Remove the .png suffix for playblast prefix
        prefix = tmp_path[:-4]
        cmds.playblast(
            frame=[frame],
            format="image",
            compression="png",
            filename=prefix,
            width=width,
            height=height,
            percent=100,
            viewer=False,
            showOrnaments=False,
            offScreen=bool(off_screen),
        )

        # playblast appends .<frame>.png
        padded = "{}.{}.png".format(prefix, str(int(frame)).zfill(4))
        img_path = padded if os.path.exists(padded) else prefix + ".png"

        with open(img_path, "rb") as fh:
            img_bytes = fh.read()
        os.unlink(img_path)

        encoded = base64.b64encode(img_bytes).decode("ascii")
        return skill_success(
            "Viewport captured ({}x{} @ frame {})".format(width, height, frame),
            image=encoded,
            width=width,
            height=height,
            frame=frame,
            off_screen=bool(off_screen),
            prompt="Use render_frame for final-quality output.",
        )
    except Exception as exc:
        return skill_exception(
            exc,
            message="Failed to capture viewport",
            possible_solutions=[
                "Pass off_screen=True if Maya is minimized or running in batch mode.",
                "Verify a model panel exists (cmds.getPanel(visiblePanels=True)).",
            ],
        )


def _no_visible_panel(cmds) -> bool:
    """Best-effort check for a usable model panel.

    Returns ``True`` when no visible model panel is detected, in which
    case playblast must run with ``offScreen=True`` to avoid hitting
    the on-screen framebuffer (which is empty for hidden / minimized
    Maya windows — issue #152).
    """
    try:
        panels = cmds.getPanel(type="modelPanel") or []
        visible = cmds.getPanel(visiblePanels=True) or []
        return not any(p in visible for p in panels)
    except Exception:  # noqa: BLE001
        return False


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`capture_viewport`."""
    return capture_viewport(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
