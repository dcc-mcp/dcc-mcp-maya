"""Query the current animation frame range and return a FrameRange-compatible dict."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_frame_range() -> dict:
    """Query the current playback / animation frame range from Maya.

    Uses ``cmds.playbackOptions`` to read the four timing values and returns
    them via the ``FrameRange``-compatible dict schema from ``dcc-mcp-core``::

        {
            "start":   <float>,   # playback start
            "end":     <float>,   # playback end
            "fps":     <float>,   # frames per second
            "current": <float>,   # current time cursor
        }

    The fps value is mapped from Maya's ``currentUnit(time=True, query=True)``
    string (e.g. ``"film"`` → 24, ``"pal"`` → 25, ``"ntsc"`` → 30,
    ``"show"`` → 48, ``"palf"`` → 50, ``"ntscf"`` → 60).

    Returns:
        ActionResultModel dict with ``context.frame_range`` (dict).
    """
    _FPS_MAP = {
        "game": 15.0,
        "film": 24.0,
        "pal": 25.0,
        "ntsc": 30.0,
        "show": 48.0,
        "palf": 50.0,
        "ntscf": 60.0,
    }

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        start = float(cmds.playbackOptions(minTime=True, query=True))
        end = float(cmds.playbackOptions(maxTime=True, query=True))
        current = float(cmds.currentTime(query=True))

        time_unit = cmds.currentUnit(time=True, query=True)
        fps = _FPS_MAP.get(time_unit, 24.0)
        # Custom fps unit: "120fps", "100fps" etc.
        if time_unit.endswith("fps"):
            try:
                fps = float(time_unit[:-3])
            except ValueError:
                fps = 24.0

        frame_range = {
            "start": start,
            "end": end,
            "fps": fps,
            "current": current,
        }

        return skill_success(
            "Frame range: {:.0f} - {:.0f} @ {:.0f} fps".format(start, end, fps),
            frame_range=frame_range,
            prompt=("Use set_timeline to change the range, or set_keyframe to add a key at the current time."),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get frame range")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_frame_range`."""
    return get_frame_range(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
