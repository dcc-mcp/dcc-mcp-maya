"""Capture the Maya viewport as a PNG image (base64-encoded)."""

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
    """Maya playblast expects a time range; a one-element list is unreliable."""
    fnum = int(round(float(frame)))
    return (fnum, fnum)


def _apply_view_fit(cmds) -> bool:
    """Fit the scene in the active model panel (correct ``allObjects`` flag)."""
    try:
        model_panels = cmds.getPanel(type="modelPanel") or []
        visible = set(cmds.getPanel(visiblePanels=True) or [])
        for panel in model_panels:
            if panel in visible:
                cmds.viewFit(panel, allObjects=True, animate=False)
                return True
        if model_panels:
            cmds.viewFit(model_panels[0], allObjects=True, animate=False)
            return True
        cmds.viewFit(allObjects=True, animate=False)
        return True
    except Exception:  # noqa: BLE001
        return False


def _read_nonempty_png(path: str) -> bytes:
    """Read a playblast PNG and fail when Maya produced an empty file."""
    with open(path, "rb") as fh:
        img_bytes = fh.read()
    if not img_bytes:
        raise ValueError("EMPTY_PLAYBLAST")
    return img_bytes


def capture_viewport(
    width: int = 1920,
    height: int = 1080,
    frame: Optional[float] = None,
    off_screen: Optional[bool] = None,
    view_fit: bool = False,
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
        view_fit: When ``True``, run ``viewFit`` with ``allObjects=True`` on the
            active model panel before capture (never use the invalid ``all=True``
            flag in ad-hoc scripts).

    Returns:
        ToolResult dict with ``context.image`` (base64 PNG string).
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")

    try:
        tmp_path: Optional[str] = None
        img_path: Optional[str] = None
        if frame is None:
            frame = cmds.currentTime(query=True)

        width, height = _clamp_playblast_dims(width, height)
        f0, f1 = _playblast_frame_range(frame)

        view_fit_applied = False
        if view_fit:
            view_fit_applied = _apply_view_fit(cmds)

        # Auto-enable off-screen rendering when Maya is running in batch
        # mode (mayapy) or when no model panel is currently focusable —
        # both are situations where on-screen capture would silently
        # produce a black frame or raise (issue #152).
        if off_screen is None:
            off_screen = bool(cmds.about(batch=True)) or _no_visible_panel(cmds)
            if view_fit and not view_fit_applied:
                off_screen = True

        # playblast writes  <prefix>.<frame_padded>.png
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Remove the .png suffix for playblast prefix
        prefix = tmp_path[:-4]
        cmds.playblast(
            frame=(f0, f1),
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
        padded = "{}.{}.png".format(prefix, str(f0).zfill(4))
        img_path = padded if os.path.exists(padded) else prefix + ".png"

        img_bytes = _read_nonempty_png(img_path)
        os.unlink(img_path)

        encoded = base64.b64encode(img_bytes).decode("ascii")
        return skill_success(
            "Viewport captured ({}x{} @ frame {})".format(width, height, frame),
            image=encoded,
            width=width,
            height=height,
            frame=frame,
            off_screen=bool(off_screen),
            view_fit=bool(view_fit),
            view_fit_applied=view_fit_applied,
            prompt="Use capture_viewport with view_fit=True instead of execute_python viewFit(all=True).",
        )
    except ValueError as exc:
        if str(exc) != "EMPTY_PLAYBLAST":
            raise
        for candidate in (tmp_path, img_path):
            try:
                if candidate and os.path.exists(candidate):
                    os.unlink(candidate)
            except OSError:
                pass
        return skill_error(
            "Viewport capture produced an empty image",
            "Maya playblast wrote a 0-byte PNG",
            possible_solutions=[
                "Pass off_screen=True if Maya is minimized or running in batch mode.",
                "Ensure a model panel is visible before capturing.",
                "Retry after using view_fit=True so the camera frames scene content.",
            ],
            error_code="EMPTY_PLAYBLAST",
            width=width,
            height=height,
            frame=frame,
            off_screen=bool(off_screen),
            view_fit=bool(view_fit),
            view_fit_applied=view_fit_applied,
        )
    except Exception as exc:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
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
