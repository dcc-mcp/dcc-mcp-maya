"""Query the status of a submitted Deadline render job by job ID."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def get_render_job_status(
    job_id: str,
    deadline_command: Optional[str] = None,
) -> dict:
    """Query Deadline for the status of a render job.

    Args:
        job_id: The Deadline job ID returned by ``submit_to_deadline``.
        deadline_command: Path to ``deadlinecommand`` binary.  If None, it
            is looked up on PATH.

    Returns:
        ActionResultModel dict with job status, progress, and task summary.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import os  # noqa: PLC0415

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

        proc = subprocess.run(
            [cmd, "-GetJobDetails", job_id],
            capture_output=True, text=True, timeout=30,
        )

        if proc.returncode != 0:
            return error_result(
                "Failed to query job '{}'".format(job_id),
                proc.stderr.strip() or proc.stdout.strip(),
            ).to_dict()

        # Parse key=value output
        status_info = {}  # type: dict
        for line in proc.stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                status_info[k.strip()] = v.strip()

        job_status = status_info.get("Status", "Unknown")
        completed = status_info.get("CompletedChunks", "0")
        total = status_info.get("TaskCount", "0")
        errors = status_info.get("FailedChunks", "0")

        return success_result(
            "Job '{}' status: {} ({}/{} tasks)".format(job_id, job_status, completed, total),
            prompt="Check again later or use submit_to_deadline to resubmit if failed.",
            job_id=job_id,
            status=job_status,
            completed_tasks=completed,
            total_tasks=total,
            failed_tasks=errors,
            raw=status_info,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_render_job_status failed")
        return error_result("Failed to query job status", str(exc)).to_dict()


def main(**kwargs):
    return get_render_job_status(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(get_render_job_status("abc-123")))
