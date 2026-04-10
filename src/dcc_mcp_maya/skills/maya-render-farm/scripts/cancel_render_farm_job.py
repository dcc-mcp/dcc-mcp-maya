"""Cancel a render farm job on Deadline."""
from __future__ import annotations

import os
import subprocess
from typing import Dict

from dcc_mcp_core import error_result, success_result


def _find_deadline_command():
    # type: () -> str
    candidates = [
        os.environ.get("DEADLINE_PATH", ""),
        r"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand.exe",
        "/opt/Thinkbox/Deadline10/bin/deadlinecommand",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return "deadlinecommand"


def run(params: Dict[str, object]):
    """Cancel a Deadline render job by job ID.

    Args:
        params: Dictionary with keys:
            - job_id (str): Deadline job ID to cancel. Required.

    Returns:
        ActionResultModel confirming cancellation.
    """
    job_id = params.get("job_id", "")
    if not job_id:
        return error_result("Missing required parameter", "Parameter 'job_id' is required")

    try:
        deadline_cmd = _find_deadline_command()
        result = subprocess.run(
            [deadline_cmd, "-FailJob", str(job_id)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return error_result(
                "Failed to cancel job", "Job {}: {}".format(job_id, result.stderr.strip())
            )

        return success_result(
            "Cancelled render farm job '{}'".format(job_id),
            prompt="Use list_render_farm_jobs to verify the job status.",
            job_id=str(job_id),
            output=result.stdout.strip(),
        )
    except Exception as exc:
        return error_result("Failed to cancel render farm job", str(exc))
