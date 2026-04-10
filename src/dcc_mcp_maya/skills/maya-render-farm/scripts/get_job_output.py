"""Get output files from a completed render farm job."""
from __future__ import annotations

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
    """Query output file paths from a Deadline render job.

    Args:
        params: Dictionary with keys:
            - job_id (str): Deadline job ID. Required.
            - check_exists (bool): Verify file existence on disk. Default False.

    Returns:
        ActionResultModel with output file list.
    """
    job_id = params.get("job_id", "")
    check_exists = bool(params.get("check_exists", False))

    if not job_id:
        return error_result("Missing required parameter", "Parameter 'job_id' is required")

    try:
        deadline_cmd = _find_deadline_command()
        result = subprocess.run(
            [deadline_cmd, "-GetJobOutputDirectories", str(job_id)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return error_result(
                "Failed to get job output", "Job {}: {}".format(job_id, result.stderr.strip())
            )

        output_dirs: List[str] = [
            line.strip() for line in result.stdout.splitlines() if line.strip()
        ]

        output_files: List[Dict[str, object]] = []
        for directory in output_dirs:
            entry: Dict[str, object] = {"directory": directory}
            if check_exists and os.path.isdir(directory):
                files = sorted(os.listdir(directory))
                entry["files"] = files
                entry["file_count"] = len(files)
            output_files.append(entry)

        return success_result(
            "Got output for job '{}' ({} directories)".format(job_id, len(output_files)),
            prompt="Check the output directories for rendered frames.",
            job_id=str(job_id),
            output_directories=output_files,
            directory_count=len(output_files),
        )
    except Exception as exc:
        return error_result("Failed to get job output", str(exc))
