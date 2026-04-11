"""Query the current scene time and playback settings."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success



def query_scene_time_info() -> dict:
    """Query the current scene time and playback settings as a single call.

    Returns a consolidated snapshot of all time-related scene settings:
    frame rate, animation range, playback range, and current time.

    Returns:
        ActionResultModel dict with ``context`` keys:
        ``fps``, ``animation_start``, ``animation_end``,
        ``playback_start``, ``playback_end``, ``current_time``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        fps = cmds.currentUnit(query=True, time=True)
        anim_start = cmds.playbackOptions(query=True, animationStartTime=True)
        anim_end = cmds.playbackOptions(query=True, animationEndTime=True)
        pb_start = cmds.playbackOptions(query=True, minTime=True)
        pb_end = cmds.playbackOptions(query=True, maxTime=True)
        current = cmds.currentTime(query=True)

        return maya_success(
            "Scene time info retrieved",
            fps=fps,
            animation_start=anim_start,
            animation_end=anim_end,
            playback_start=pb_start,
            playback_end=pb_end,
            current_time=current,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to query scene time info")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`query_scene_time_info`."""
    return query_scene_time_info(**kwargs)


if __name__ == "__main__":
    import json

    result = query_scene_time_info()
    print(json.dumps(result))
