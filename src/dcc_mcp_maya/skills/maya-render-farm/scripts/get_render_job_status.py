"""Query the status of a submitted Deadline render job by job ID."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import subprocess
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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

    try:
        import os  # noqa: PLC0415

        cmd = deadline_command
        if not cmd:
            for candidate in ["deadlinecommand", "deadlinecommand.exe"]:
                result = subprocess.run(
                    ["where", candidate] if os.name == "nt" else ["which", candidate], capture_output=True, text=True
                )
                if result.returncode == 0:
                    cmd = candidate
                    break
        if not cmd:
            return skill_error(
                "deadlinecommand not found",
                "Install Thinkbox Deadline client and ensure it is on PATH",
            )

        proc = subprocess.run(
            [cmd, "-GetJobDetails", job_id],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if proc.returncode != 0:
            return skill_error(
                "Failed to query job '{}'".format(job_id),
                proc.stderr.strip() or proc.stdout.strip(),
            )

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

        return skill_success(
            "Job '{}' status: {} ({}/{} tasks)".format(job_id, job_status, completed, total),
            prompt="Check again later or use submit_to_deadline to resubmit if failed.",
            job_id=job_id,
            status=job_status,
            completed_tasks=completed,
            total_tasks=total,
            failed_tasks=errors,
            raw=status_info,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to query job status")


@skill_entry
def main(**kwargs):
    return get_render_job_status(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
