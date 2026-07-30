"""Render an inclusive Maya frame range with the active renderer."""

from __future__ import annotations

import importlib.util
import os
import time
from typing import Optional

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.dispatcher import check_maya_cancelled


def _render_frame_function():
    path = os.path.join(os.path.dirname(__file__), "render_frame.py")
    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_render_frame_for_sequence", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_frame


def render_sequence(
    camera: str,
    output_dir: str,
    start_frame: int = 1,
    end_frame: int = 360,
    width: Optional[int] = None,
    height: Optional[int] = None,
    output_prefix: str = "maya_lookdev",
) -> dict:
    """Render every frame from ``start_frame`` through ``end_frame``."""
    try:
        first = int(start_frame)
        last = int(end_frame)
        if last < first or last - first + 1 > 10000:
            return skill_error(
                "Invalid frame range",
                "end_frame must be >= start_frame and the range must contain at most 10000 frames",
            )

        render_frame = _render_frame_function()
        outputs = []
        started = time.time()
        for frame in range(first, last + 1):
            check_maya_cancelled()
            result = render_frame(
                camera=camera,
                frame=frame,
                width=width,
                height=height,
                output_dir=output_dir,
                output_name="{}_{:04d}".format(output_prefix, frame),
                return_base64=False,
            )
            if not result.get("success"):
                return skill_error(
                    "Sequence render failed at frame {}".format(frame),
                    result.get("message") or result.get("error") or "render_frame failed",
                    failed_frame=frame,
                    completed_frames=len(outputs),
                )
            outputs.append(result["context"]["output_path"])

        return skill_success(
            "Rendered {} frames to {}".format(len(outputs), output_dir),
            frame_count=len(outputs),
            start_frame=first,
            end_frame=last,
            output_dir=output_dir,
            output_prefix=output_prefix,
            first_output=outputs[0],
            middle_output=outputs[len(outputs) // 2],
            last_output=outputs[-1],
            elapsed_seconds=round(time.time() - started, 3),
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to render frame sequence")


@skill_entry
def main(**kwargs) -> dict:
    return render_sequence(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
