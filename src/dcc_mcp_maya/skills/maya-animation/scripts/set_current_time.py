"""Set the current frame number."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def set_current_time(frame: float) -> dict:
    """Set the current frame number.

    Args:
        frame: Target frame number.

    Returns:
        ActionResultModel dict with ``context.current_time``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.currentTime(frame, update=True)
        return skill_success(
            "Current time set to {}".format(frame),
            current_time=frame,
            prompt="Use get_current_time to verify or set_keyframe to record the pose.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set current time")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_current_time`."""
    return set_current_time(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
