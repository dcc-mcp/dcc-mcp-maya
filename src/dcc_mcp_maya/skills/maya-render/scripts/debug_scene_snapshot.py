"""Collect a compact scene debug snapshot for agents."""

from __future__ import annotations

import importlib.util
import os
from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _safe_call(default, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return default


def _short_name(long_name: str) -> str:
    return long_name.rsplit("|", 1)[-1] if "|" in long_name else long_name


def _scene_summary(cmds, max_nodes: int) -> Dict[str, Any]:
    transforms = cmds.ls(type="transform", long=True) or []
    cameras = cmds.ls(type="camera") or []
    lights = []
    for light_type in ("light", "directionalLight", "pointLight", "spotLight", "areaLight", "aiSkyDomeLight"):
        for node in _safe_call([], cmds.ls, type=light_type) or []:
            if node not in lights:
                lights.append(node)
    meshes = cmds.ls(type="mesh") or []
    sample_nodes: List[Dict[str, Any]] = []
    for node in transforms[: max(0, int(max_nodes))]:
        sample_nodes.append(
            {
                "name": _short_name(node),
                "long_name": node,
                "object_type": _safe_call(None, cmds.objectType, node),
                "parent": (_safe_call([], cmds.listRelatives, node, parent=True, fullPath=True) or [None])[0],
                "children": _safe_call([], cmds.listRelatives, node, children=True, fullPath=True) or [],
                "visible": bool(_safe_call(True, cmds.getAttr, node + ".visibility")),
            }
        )
    scene_path = _safe_call(None, cmds.file, query=True, sceneName=True) or None
    return {
        "scene_path": scene_path,
        "transform_count": len(transforms),
        "mesh_count": len(meshes),
        "camera_count": len(cameras),
        "light_count": len(lights),
        "sample_nodes": sample_nodes,
        "truncated": len(transforms) > len(sample_nodes),
    }


def _load_sibling_function(script_name: str, function_name: str):
    script_path = os.path.join(os.path.dirname(__file__), "{}.py".format(script_name))
    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_{}_for_snapshot".format(script_name), script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, function_name)


def _capture_preview(
    camera: Optional[str],
    frame: Optional[float],
    width: int,
    height: int,
    return_base64: bool,
) -> dict:
    render_frame = _load_sibling_function("render_frame", "render_frame")
    return render_frame(
        camera=camera,
        frame=frame,
        width=width,
        height=height,
        output_name="debug_scene_snapshot",
        return_base64=return_base64,
    )


def _capture_ui(object_name: Optional[str]) -> Optional[dict]:
    try:
        from dcc_mcp_maya import _dev_session  # noqa: PLC0415

        return _dev_session.capture_ui(object_name=object_name)
    except Exception as exc:
        return skill_exception(exc, message="Failed to capture Maya UI for debug snapshot")


def debug_scene_snapshot(
    max_nodes: int = 50,
    include_preview: bool = True,
    include_ui: bool = False,
    camera: Optional[str] = None,
    frame: Optional[float] = None,
    preview_width: int = 640,
    preview_height: int = 480,
    return_base64: bool = True,
    ui_object_name: Optional[str] = None,
) -> dict:
    """Return scene structure plus optional visual debug evidence."""

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        max_nodes = max(1, min(int(max_nodes), 500))
        preview_width = max(1, min(int(preview_width), 8192))
        preview_height = max(1, min(int(preview_height), 8192))
        summary = _scene_summary(cmds, max_nodes)

        preview = None
        if include_preview:
            preview = _capture_preview(camera, frame, preview_width, preview_height, bool(return_base64))

        ui_capture = None
        if include_ui:
            ui_capture = _capture_ui(ui_object_name)

        ok = True
        if preview is not None and not preview.get("success", False):
            ok = False
        if ui_capture is not None and not ui_capture.get("success", False):
            ok = False

        message = "Scene debug snapshot collected"
        if not ok:
            message = "Scene debug snapshot collected with partial visual evidence"
        return skill_success(
            message,
            scene_summary=summary,
            preview=preview,
            ui_capture=ui_capture,
            include_preview=bool(include_preview),
            include_ui=bool(include_ui),
            prompt="Use scene_summary for structure, preview for camera-visible scene pixels, and ui_capture for Maya window state.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to collect scene debug snapshot")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`debug_scene_snapshot`."""
    return debug_scene_snapshot(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
