"""Shared, read-only Maya viewport capture preflight."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_error


def inspect_viewport_capture_availability(cmds: Any) -> Dict[str, Any]:
    """Return whether viewport capture has a visible GUI rendering surface.

    Batch Maya has no main window and retains the existing off-screen capture
    path.  Interactive Maya must have both a visible main window and a visible
    model panel; otherwise VP2 may write a valid-looking solid white image.
    """
    try:
        batch = bool(cmds.about(batch=True))
    except Exception:  # noqa: BLE001
        batch = False

    window_exists: Optional[bool] = None
    window_visible: Optional[bool] = None
    try:
        window_exists = bool(cmds.window("MayaWindow", exists=True))
        if window_exists:
            window_visible = bool(cmds.window("MayaWindow", query=True, visible=True))
    except Exception:  # noqa: BLE001
        pass

    panels: List[str] = []
    visible_panels: List[str] = []
    try:
        panels = [str(panel) for panel in (cmds.getPanel(type="modelPanel") or [])]
        visible = set(str(panel) for panel in (cmds.getPanel(visiblePanels=True) or []))
        visible_panels = [panel for panel in panels if panel in visible]
    except Exception:  # noqa: BLE001
        pass

    reason: Optional[str] = None
    if not batch and window_exists and window_visible is False:
        reason = "maya_window_hidden"
    elif not batch and not visible_panels:
        reason = "no_visible_model_panel"

    return {
        "available": reason is None,
        "reason": reason,
        "batch": batch,
        "maya_window_exists": window_exists,
        "maya_window_visible": window_visible,
        "model_panels": panels,
        "visible_model_panels": visible_panels,
    }


def viewport_capture_preflight(cmds: Any) -> Optional[Dict[str, Any]]:
    """Return a typed tool error when interactive viewport capture is unsafe."""
    availability = inspect_viewport_capture_availability(cmds)
    if availability["available"]:
        return None
    return skill_error(
        "Maya viewport is unavailable for capture",
        "Interactive viewport capture requires a visible Maya window and model panel.",
        error_code="MAYA_VIEWPORT_UNAVAILABLE",
        reason=availability["reason"],
        maya_window_exists=availability["maya_window_exists"],
        maya_window_visible=availability["maya_window_visible"],
        model_panels=availability["model_panels"],
        visible_model_panels=availability["visible_model_panels"],
        possible_solutions=[
            "Make the Maya main window and a model panel visible, then retry.",
            "Use maya_render__render_frame when an interactive viewport is unavailable.",
        ],
    )
