"""Set the current frame number."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
        return maya_success(
            "Current time set to {}".format(frame),
            current_time=frame,
            prompt="Use get_current_time to verify or set_keyframe to record the pose.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set current time")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_current_time`."""
    return set_current_time(**kwargs)


if __name__ == "__main__":
    import json

    result = set_current_time()
    print(json.dumps(result))
