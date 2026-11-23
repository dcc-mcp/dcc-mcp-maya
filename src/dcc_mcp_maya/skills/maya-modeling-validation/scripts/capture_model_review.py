"""Capture repeatable fixed-view modeling review evidence."""

from __future__ import annotations

import importlib.util
import os
from typing import List, Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def _load_render_frame():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "maya-render", "scripts", "render_frame.py")
    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_render_frame_for_model_review", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Maya render_frame")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_frame


def capture_model_review(
    camera: Optional[str] = None,
    frame: Optional[float] = None,
    width: int = 1024,
    height: int = 1024,
    object_names: Optional[List[str]] = None,
    return_base64: bool = True,
) -> dict:
    """Render one fixed camera/frame review image and return structured evidence."""
    if isinstance(width, bool) or not isinstance(width, int) or not 1 <= width <= 4096:
        return skill_error("Invalid review width", "width must be an integer from 1 to 4096")
    if isinstance(height, bool) or not isinstance(height, int) or not 1 <= height <= 4096:
        return skill_error("Invalid review height", "height must be an integer from 1 to 4096")
    if object_names is not None and (not isinstance(object_names, list) or len(object_names) > 128):
        return skill_error("Invalid review scope", "object_names must contain at most 128 names")
    try:
        import maya.cmds as cmds

        missing = [name for name in object_names or [] if not cmds.objExists(name)]
        if missing:
            return skill_error("Review scope contains missing objects", "Maya object does not exist", missing=missing)
        render_frame = _load_render_frame()
        result = render_frame(
            camera=camera,
            frame=frame,
            width=width,
            height=height,
            output_name="model_review",
            return_base64=bool(return_base64),
        )
        if not result.get("success"):
            return skill_error(
                "Model review capture failed",
                result.get("message", "Maya render_frame failed"),
                render_result=result,
                object_names=object_names or [],
            )
        render_context = result.get("context", {})
        return skill_success(
            "Fixed-view model review captured",
            evidence={
                "camera": render_context.get("camera"),
                "frame": render_context.get("frame"),
                "width": render_context.get("width", width),
                "height": render_context.get("height", height),
                "object_names": object_names or [],
                "fixed_view": True,
                "output_path": render_context.get("output_path"),
                "output_size": render_context.get("output_size"),
                "image_base64": render_context.get("image_base64"),
            },
            prompt="Pass evidence.camera and evidence.frame with the model-state export to the acceptance report.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to capture fixed-view model review")


@skill_entry
def main(**kwargs) -> dict:
    return capture_model_review(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
