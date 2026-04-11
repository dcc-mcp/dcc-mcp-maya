"""Query the current scene time and playback settings."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def query_scene_time_info() -> dict:
    """Query the current scene time and playback settings as a single call.

    Returns a consolidated snapshot of all time-related scene settings:
    frame rate, animation range, playback range, and current time.

    Returns:
        ActionResultModel dict with ``context`` keys:
        ``fps``, ``animation_start``, ``animation_end``,
        ``playback_start``, ``playback_end``, ``current_time``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        fps = cmds.currentUnit(query=True, time=True)
        anim_start = cmds.playbackOptions(query=True, animationStartTime=True)
        anim_end = cmds.playbackOptions(query=True, animationEndTime=True)
        pb_start = cmds.playbackOptions(query=True, minTime=True)
        pb_end = cmds.playbackOptions(query=True, maxTime=True)
        current = cmds.currentTime(query=True)

        return success_result(
            "Scene time info retrieved",
            fps=fps,
            animation_start=anim_start,
            animation_end=anim_end,
            playback_start=pb_start,
            playback_end=pb_end,
            current_time=current,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("query_scene_time_info failed")
        return error_result("Failed to query scene time info", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`query_scene_time_info`."""
    return query_scene_time_info(**kwargs)


if __name__ == "__main__":
    import json

    result = query_scene_time_info()
    print(json.dumps(result))
