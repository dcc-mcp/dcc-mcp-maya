"""Submit a Maya render job to Deadline render farm."""
from __future__ import annotations

import os
import subprocess
from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def _find_deadline_command():
    # type: () -> Optional[str]
    """Locate the Deadline command-line client binary."""
    candidates = [
        os.environ.get("DEADLINE_PATH", ""),
        r"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand.exe",
        "/opt/Thinkbox/Deadline10/bin/deadlinecommand",
        "/Applications/Deadline/bin/deadlinecommand",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    # Try PATH
    return "deadlinecommand"


def run(params: Dict[str, object]):
    """Submit the current Maya scene to Deadline.

    Args:
        params: Dictionary with keys:
            - job_name (str): Job name. Default 'Maya_Render'.
            - frames (str): Frame list e.g. '1-100' or '1,5,10'. Default '1'.
            - renderer (str): Renderer name e.g. 'arnold', 'vray'. Default 'arnold'.
            - output_dir (str): Output directory. Default scene workspace images dir.
            - pool (str): Deadline pool name. Default 'none'.
            - priority (int): Job priority 0-100. Default 50.
            - chunk_size (int): Frames per task. Default 1.

    Returns:
        ActionResultModel with Deadline job ID.
    """
    scene_path = cmds.file(query=True, sceneName=True)
    job_name = params.get("job_name", "Maya_Render")
    frames = params.get("frames", "1")
    renderer = params.get("renderer", "arnold")
    output_dir = params.get("output_dir", cmds.workspace(query=True, rootDirectory=True) + "images")
    pool = params.get("pool", "none")
    priority = int(params.get("priority", 50))
    chunk_size = int(params.get("chunk_size", 1))

    if not scene_path:
        return error_result("No scene open", "Please save the scene before submitting")

    try:
        job_info = {
            "Plugin": "MayaBatch",
            "Name": str(job_name),
            "Frames": str(frames),
            "ChunkSize": str(chunk_size),
            "Pool": str(pool),
            "Priority": str(priority),
        }
        plugin_info = {
            "SceneFile": scene_path,
            "Renderer": str(renderer),
            "OutputDirectory0": str(output_dir),
            "Version": cmds.about(version=True),
        }

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix="_job.ini", delete=False) as jf:
            jf.write("\n".join("{}={}".format(k, v) for k, v in job_info.items()))
            job_file = jf.name
        with tempfile.NamedTemporaryFile(mode="w", suffix="_plugin.ini", delete=False) as pf:
            pf.write("\n".join("{}={}".format(k, v) for k, v in plugin_info.items()))
            plugin_file = pf.name

        deadline_cmd = _find_deadline_command()
        result = subprocess.run(
            [deadline_cmd, job_file, plugin_file],
            capture_output=True, text=True, timeout=30,
        )
        os.unlink(job_file)
        os.unlink(plugin_file)

        if result.returncode != 0:
            return error_result("Deadline submission failed", result.stderr.strip())

        job_id = result.stdout.strip().split()[-1] if result.stdout.strip() else "unknown"

        return success_result(
            "Submitted Deadline job '{}' (ID: {})".format(job_name, job_id),
            prompt="Use list_render_farm_jobs to monitor job status.",
            job_id=job_id,
            job_name=str(job_name),
            frames=str(frames),
            renderer=str(renderer),
        )
    except Exception as exc:
        return error_result("Failed to submit Deadline job", str(exc))
