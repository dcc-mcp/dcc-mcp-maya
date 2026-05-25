"""Set a model panel to look through a Maya camera."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, validate_node_exists


def _active_model_panel(cmds) -> Optional[str]:
    try:
        focused = cmds.getPanel(withFocus=True)
        if focused and cmds.getPanel(typeOf=focused) == "modelPanel":
            return str(focused)
    except Exception:  # noqa: BLE001
        pass
    try:
        panels = cmds.getPanel(type="modelPanel") or []
        visible = set(cmds.getPanel(visiblePanels=True) or [])
    except Exception:  # noqa: BLE001
        return None
    for panel in panels:
        if panel in visible:
            return str(panel)
    return str(panels[0]) if panels else None


def _panel_camera(cmds, panel: Optional[str]) -> Optional[str]:
    if not panel:
        return None
    try:
        return str(cmds.modelPanel(panel, query=True, camera=True))
    except Exception:  # noqa: BLE001
        return None


def look_through_camera(camera: str, panel: Optional[str] = None, view_fit: bool = False) -> dict:
    """Switch a model panel to look through *camera*."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, camera)
        if err:
            return err
        target_panel = panel or _active_model_panel(cmds)
        if not target_panel:
            return maya_error(
                "No model panel available",
                "Could not find a modelPanel to switch to the requested camera.",
            )
        previous_camera = _panel_camera(cmds, target_panel)
        cmds.lookThru(target_panel, camera)
        view_fit_applied = False
        if view_fit:
            try:
                cmds.viewFit(target_panel, allObjects=True, animate=False)
                view_fit_applied = True
            except Exception:  # noqa: BLE001
                view_fit_applied = False

        return maya_success(
            "Panel {} is now looking through {}".format(target_panel, camera),
            panel=target_panel,
            camera=camera,
            previous_camera=previous_camera,
            view_fit=bool(view_fit),
            view_fit_applied=view_fit_applied,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to switch viewport camera")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`look_through_camera`."""
    return look_through_camera(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
