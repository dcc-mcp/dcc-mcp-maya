"""List render farm jobs from Deadline."""
from __future__ import annotations

import json
import os
import subprocess
from typing import Dict, List

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
    """List render farm jobs from Deadline with optional status filter.

    Args:
        params: Dictionary with keys:
            - status (str): Filter by status: 'active', 'completed', 'failed', 'all'. Default 'all'.
            - limit (int): Maximum number of jobs to return. Default 20.

    Returns:
        ActionResultModel with list of job information.
    """
    status_filter = str(params.get("status", "all")).lower()
    limit = int(params.get("limit", 20))

    try:
        deadline_cmd = _find_deadline_command()
        result = subprocess.run(
            [deadline_cmd, "-GetJobs"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return error_result("Deadline query failed", result.stderr.strip())

        raw_jobs: List[Dict[str, object]] = []
        try:
            raw_jobs = json.loads(result.stdout) if result.stdout.strip() else []
        except json.JSONDecodeError:
            # Parse simple key=value output
            for line in result.stdout.splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    raw_jobs.append({"Name": k.strip(), "Status": v.strip()})

        jobs: List[Dict[str, object]] = []
        for job in raw_jobs:
            job_status = str(job.get("Status", "")).lower()
            if status_filter != "all" and job_status != status_filter:
                continue
            jobs.append({
                "id": job.get("JobId", job.get("ID", "")),
                "name": job.get("Name", ""),
                "status": job.get("Status", ""),
                "frames": job.get("Frames", ""),
                "priority": job.get("Priority", ""),
            })
            if len(jobs) >= limit:
                break

        return success_result(
            "Found {} render farm job(s)".format(len(jobs)),
            prompt="Use cancel_render_farm_job to cancel a running job.",
            jobs=jobs,
            count=len(jobs),
            status_filter=status_filter,
        )
    except Exception as exc:
        return error_result("Failed to list render farm jobs", str(exc))
