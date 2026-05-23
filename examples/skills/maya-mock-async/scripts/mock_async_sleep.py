"""Synthetic async tool for gateway integration tests.

Sleeps for ``duration_secs`` seconds, yielding a progress checkpoint every
``progress_interval_secs``.  Respects cooperative cancellation via
:func:`dcc_mcp_maya.dispatcher.check_maya_cancelled` so integration tests
can verify that cancellation signals propagate end-to-end through the
gateway.

No actual Maya installation is required — this skill is designed to work
with ``MayaStandaloneDispatcher``.
"""

from __future__ import annotations

import time

from dcc_mcp_core.skill import skill_entry, skill_success


@skill_entry
def mock_async_sleep(
    duration_secs: float = 2.0,
    progress_interval_secs: float = 0.5,
    **kwargs,
):
    """Sleep for *duration_secs* seconds, checking for cancellation every interval.

    Parameters
    ----------
    duration_secs:
        Total sleep duration in seconds.
    progress_interval_secs:
        How often to check for cancellation and log progress.
    """
    try:
        from dcc_mcp_maya.dispatcher import check_maya_cancelled  # noqa: PLC0415
    except ImportError:

        def check_maya_cancelled():  # type: ignore[misc]
            pass

    deadline = time.monotonic() + duration_secs
    slept = 0.0

    while time.monotonic() < deadline:
        check_maya_cancelled()
        chunk = min(progress_interval_secs, deadline - time.monotonic())
        if chunk <= 0:
            break
        time.sleep(chunk)
        slept += chunk

    return skill_success(
        f"Slept {slept:.2f}s of {duration_secs}s",
        prompt="Use jobs_get_status to check completion.",
        slept_secs=round(slept, 3),
        cancelled=False,
    )


def main(**kwargs):
    return mock_async_sleep(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
