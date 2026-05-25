"""Query the active Maya viewport camera."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def _safe_get_attr(cmds: Any, plug: str) -> Any:
    try:
        exists = getattr(cmds, "objExists", None)
        if callable(exists) and not exists(plug):
            return None
    except Exception:  # noqa: BLE001
        pass
    try:
        value = cmds.getAttr(plug)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], tuple):
        return list(value[0])
    return value


def _panel_type(cmds: Any, panel: Optional[str]) -> Optional[str]:
    if not panel:
        return None
    try:
        return str(cmds.getPanel(typeOf=panel))
    except Exception:  # noqa: BLE001
        return None


def _active_model_panel(cmds: Any) -> Optional[str]:
    try:
        focused = cmds.getPanel(withFocus=True)
    except Exception:  # noqa: BLE001
        focused = None
    if _panel_type(cmds, focused) == "modelPanel":
        return str(focused)

    try:
        visible = set(cmds.getPanel(visiblePanels=True) or [])
        panels = cmds.getPanel(type="modelPanel") or []
    except Exception:  # noqa: BLE001
        return None
    for panel in panels:
        if panel in visible:
            return str(panel)
    return str(panels[0]) if panels else None


def _camera_from_panel(cmds: Any, panel: Optional[str]) -> Optional[str]:
    if not panel:
        return None
    try:
        return str(cmds.modelPanel(panel, query=True, camera=True))
    except Exception:  # noqa: BLE001
        return None


def _camera_shape(cmds: Any, camera: str) -> Optional[str]:
    try:
        if cmds.nodeType(camera) == "camera":
            return camera
    except Exception:  # noqa: BLE001
        pass
    try:
        shapes = cmds.listRelatives(camera, shapes=True, fullPath=False) or []
    except Exception:  # noqa: BLE001
        shapes = []
    for shape in shapes:
        try:
            if cmds.nodeType(shape) == "camera":
                return str(shape)
        except Exception:  # noqa: BLE001
            continue
    return None


def _camera_transform(cmds: Any, camera_shape: str) -> str:
    try:
        parents = cmds.listRelatives(camera_shape, parent=True, fullPath=False) or []
        if parents:
            return str(parents[0])
    except Exception:  # noqa: BLE001
        pass
    return camera_shape


def _camera_summary(cmds: Any, camera: str, panel: Optional[str], source: str) -> Dict[str, Any]:
    shape = _camera_shape(cmds, camera)
    transform = _camera_transform(cmds, shape) if shape else camera
    return {
        "camera": transform,
        "camera_shape": shape,
        "panel": panel,
        "source": source,
        "focal_length": _safe_get_attr(cmds, "{}.focalLength".format(shape)) if shape else None,
        "horizontal_film_aperture": _safe_get_attr(cmds, "{}.horizontalFilmAperture".format(shape)) if shape else None,
        "vertical_film_aperture": _safe_get_attr(cmds, "{}.verticalFilmAperture".format(shape)) if shape else None,
        "renderable": _safe_get_attr(cmds, "{}.renderable".format(shape)) if shape else None,
    }


def _all_cameras(cmds: Any) -> List[Dict[str, Any]]:
    try:
        shapes = [str(item) for item in (cmds.ls(type="camera") or [])]
    except Exception:  # noqa: BLE001
        shapes = []
    cameras = []
    for shape in shapes:
        transform = _camera_transform(cmds, shape)
        cameras.append(_camera_summary(cmds, transform, None, "scene"))
    return cameras


def get_viewport_camera() -> dict:
    """Return the focused model panel camera, with scene-camera fallback."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        panel = _active_model_panel(cmds)
        camera = _camera_from_panel(cmds, panel)
        source = "focused_model_panel" if camera else "scene_camera_fallback"
        all_cameras = _all_cameras(cmds)
        if not camera and all_cameras:
            camera = str(all_cameras[0]["camera"])

        if not camera:
            return maya_error(
                "No Maya camera found",
                "Could not find an active model panel camera or any camera nodes in the scene.",
            )

        summary = _camera_summary(cmds, camera, panel, source)
        return maya_success(
            "Viewport camera: {}".format(summary["camera"]),
            **summary,
            cameras=all_cameras,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to query viewport camera")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_viewport_camera`."""
    return get_viewport_camera(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
