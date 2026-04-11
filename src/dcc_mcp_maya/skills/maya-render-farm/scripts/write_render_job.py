"""Write a JSON render job specification for a render farm dispatcher."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def write_render_job(
    output_dir: str,
    job_name: Optional[str] = None,
    renderer: Optional[str] = None,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    step: int = 1,
    chunk_size: int = 10,
    priority: int = 50,
) -> dict:
    """Write a render job JSON spec from the current scene settings.

    Args:
        output_dir: Directory where the ``.json`` job file is written.
        job_name: Job display name.  Defaults to the scene file stem.
        renderer: Override render engine name (e.g. ``"arnold"``, ``"vray"``).
            Defaults to the scene's active renderer.
        start_frame: Override start frame.  Defaults to scene render globals.
        end_frame: Override end frame.  Defaults to scene render globals.
        step: Frame step / increment.  Default: 1.
        chunk_size: Frames per render task.  Default: 10.
        priority: Job priority (0=low, 100=high).  Default: 50.

    Returns:
        ActionResultModel dict with ``context.job_file`` path and job spec summary.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        scene_path = cmds.file(q=True, sceneName=True) or ""
        scene_stem = os.path.splitext(os.path.basename(scene_path))[0] or "untitled"

        name = job_name or scene_stem

        sf = start_frame if start_frame is not None else int(cmds.getAttr("defaultRenderGlobals.startFrame"))
        ef = end_frame if end_frame is not None else int(cmds.getAttr("defaultRenderGlobals.endFrame"))

        active_renderer = renderer
        if not active_renderer:
            try:
                active_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
            except Exception:
                active_renderer = "mayaSoftware"

        render_output = cmds.workspace(q=True, rootDirectory=True) or ""
        try:
            render_output = cmds.workspace(renderType="images", q=True, fullName=True) or render_output
        except Exception:
            pass

        job_spec = {
            "name": name,
            "scene_file": scene_path,
            "renderer": active_renderer,
            "start_frame": sf,
            "end_frame": ef,
            "step": step,
            "chunk_size": chunk_size,
            "priority": priority,
            "output_dir": render_output,
        }

        os.makedirs(output_dir, exist_ok=True)
        job_file = os.path.join(output_dir, "{}.json".format(name))
        with open(job_file, "w") as fh:
            json.dump(job_spec, fh, indent=2)

        frame_count = max(0, (ef - sf) // step + 1)
        task_count = max(1, (frame_count + chunk_size - 1) // chunk_size)

        return success_result(
            "Wrote render job spec '{}' to '{}'".format(name, job_file),
            prompt="Use submit_to_deadline to send this job to the render farm.",
            job_file=job_file,
            name=name,
            renderer=active_renderer,
            frame_range="{}-{}".format(sf, ef),
            frame_count=frame_count,
            task_count=task_count,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("write_render_job failed")
        return error_result("Failed to write render job", str(exc)).to_dict()


def main(**kwargs):
    return write_render_job(**kwargs)


if __name__ == "__main__":
    import json as _json

    print(_json.dumps(write_render_job("/tmp/jobs")))
