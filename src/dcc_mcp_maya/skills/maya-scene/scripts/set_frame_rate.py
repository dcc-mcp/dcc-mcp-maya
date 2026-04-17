"""Change the scene's playback frame rate."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


def set_frame_rate(fps: str = "film") -> dict:
    """Change the scene's playback frame rate.

    Args:
        fps: A Maya time-unit string or numeric alias.  Common values:

            * ``"game"``  – 15 fps
            * ``"film"``  – 24 fps  *(default)*
            * ``"pal"``   – 25 fps
            * ``"ntsc"``  – 30 fps
            * ``"show"``  – 48 fps
            * ``"palf"``  – 50 fps
            * ``"ntscf"`` – 60 fps

    Returns:
        ToolResult dict with ``context.fps`` (the applied setting).
    """

    _VALID_FPS = {
        "game",
        "film",
        "pal",
        "ntsc",
        "show",
        "palf",
        "ntscf",
        "23.976fps",
        "29.97fps",
        "47.952fps",
        "59.94fps",
        "44100fps",
        "48000fps",
    }

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if fps not in _VALID_FPS:
            return skill_error(
                "Invalid frame rate: '{}'".format(fps),
                "Valid values: {}".format(", ".join(sorted(_VALID_FPS))),
            )

        cmds.currentUnit(time=fps)
        actual = cmds.currentUnit(query=True, time=True)
        return skill_success(
            "Frame rate set to '{}'".format(actual),
            fps=actual,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set frame rate to '{}'".format(fps))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_frame_rate`."""
    return set_frame_rate(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
