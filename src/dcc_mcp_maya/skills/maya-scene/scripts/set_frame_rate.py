"""Change the scene's playback frame rate."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
        ActionResultModel dict with ``context.fps`` (the applied setting).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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
            return error_result(
                "Invalid frame rate: '{}'".format(fps),
                "Valid values: {}".format(", ".join(sorted(_VALID_FPS))),
            ).to_dict()

        cmds.currentUnit(time=fps)
        actual = cmds.currentUnit(query=True, time=True)
        return success_result(
            "Frame rate set to '{}'".format(actual),
            fps=actual,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_frame_rate failed")
        return error_result("Failed to set frame rate to '{}'".format(fps), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_frame_rate`."""
    return set_frame_rate(**kwargs)


if __name__ == "__main__":
    import json

    result = set_frame_rate()
    print(json.dumps(result))
