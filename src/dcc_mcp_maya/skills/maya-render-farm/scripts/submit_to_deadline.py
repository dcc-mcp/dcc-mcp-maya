"""Submit the current Maya scene to Thinkbox Deadline render farm."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def submit_to_deadline(
    job_name: Optional[str] = None,
    pool: str = "maya",
    priority: int = 50,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    chunk_size: int = 10,
    deadline_command: Optional[str] = None,
) -> dict:
    """Submit the current Maya scene to Thinkbox Deadline.

    Requires the Deadline client to be installed and ``deadlinecommand`` (or
    ``deadlinecommand.exe``) to be on the system PATH, or passed explicitly.

    Args:
        job_name: Display name for the Deadline job.  Defaults to scene stem.
        pool: Deadline worker pool name.  Default: ``"maya"``.
        priority: Job priority 0-100.  Default: 50.
        start_frame: Override start frame.
        end_frame: Override end frame.
        chunk_size: Frames per task.  Default: 10.
        deadline_command: Path to ``deadlinecommand`` binary.  If None, the
            tool is looked up on PATH.

    Returns:
        ActionResultModel dict with the Deadline job ID on success.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        scene_path = cmds.file(q=True, sceneName=True) or ""
        if not scene_path:
            return error_result(
                "Scene must be saved before submitting",
                "Save the scene first with save_scene",
            ).to_dict()

        scene_stem = os.path.splitext(os.path.basename(scene_path))[0]
        name = job_name or scene_stem

        sf = start_frame if start_frame is not None else int(
            cmds.getAttr("defaultRenderGlobals.startFrame")
        )
        ef = end_frame if end_frame is not None else int(
            cmds.getAttr("defaultRenderGlobals.endFrame")
        )

        # Locate deadlinecommand
        cmd = deadline_command
        if not cmd:
            for candidate in ["deadlinecommand", "deadlinecommand.exe"]:
                result = subprocess.run(
                    ["where", candidate] if os.name == "nt" else ["which", candidate],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    cmd = candidate
                    break
        if not cmd:
            return error_result(
                "deadlinecommand not found",
                "Install Thinkbox Deadline client and ensure it is on PATH",
            ).to_dict()

        # Build minimal job info files
        job_info = {
            "Plugin": "MayaBatch",
            "Name": name,
            "Pool": pool,
            "Priority": str(priority),
            "Frames": "{}-{}".format(sf, ef),
            "ChunkSize": str(chunk_size),
        }
        plugin_info = {
            "SceneFile": scene_path,
            "Version": cmds.about(version=True) or "2024",
            "Renderer": cmds.getAttr("defaultRenderGlobals.currentRenderer"),
        }

        with tempfile.TemporaryDirectory() as tmp:
            job_file = os.path.join(tmp, "job_info.job")
            plugin_file = os.path.join(tmp, "plugin_info.job")

            with open(job_file, "w") as fh:
                for k, v in job_info.items():
                    fh.write("{}={}\n".format(k, v))
            with open(plugin_file, "w") as fh:
                for k, v in plugin_info.items():
                    fh.write("{}={}\n".format(k, v))

            proc = subprocess.run(
                [cmd, job_file, plugin_file],
                capture_output=True, text=True, timeout=60,
            )

        if proc.returncode != 0:
            return error_result(
                "Deadline submission failed",
                proc.stderr.strip() or proc.stdout.strip(),
            ).to_dict()

        # Parse job ID from output
        job_id = ""
        for line in proc.stdout.splitlines():
            if "JobID" in line or "Job ID" in line:
                parts = line.split("=", 1) if "=" in line else line.split(":", 1)
                if len(parts) == 2:
                    job_id = parts[1].strip()
                    break

        return success_result(
            "Submitted '{}' to Deadline (job ID: {})".format(name, job_id or "unknown"),
            prompt="Use get_render_job_status with the job ID to monitor progress.",
            job_id=job_id,
            name=name,
            pool=pool,
            frame_range="{}-{}".format(sf, ef),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("submit_to_deadline failed")
        return error_result("Failed to submit to Deadline", str(exc)).to_dict()


def main(**kwargs):
    return submit_to_deadline(**kwargs)


if __name__ == "__main__":
    import json as _json

    print(_json.dumps(submit_to_deadline()))
