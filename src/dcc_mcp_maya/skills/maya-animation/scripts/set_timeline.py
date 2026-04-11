"""Set the playback and animation timeline range."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def set_timeline(
    start_frame: float = 1.0,
    end_frame: float = 120.0,
    min_frame: Optional[float] = None,
    max_frame: Optional[float] = None,
) -> dict:
    """Set the playback and animation timeline range.

    Args:
        start_frame: Playback start frame.  Default: 1.
        end_frame: Playback end frame.  Default: 120.
        min_frame: Animation range minimum (inner range).  Defaults to
            ``start_frame`` if not specified.
        max_frame: Animation range maximum (inner range).  Defaults to
            ``end_frame`` if not specified.

    Returns:
        ActionResultModel dict with timeline range info.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if min_frame is None:
            min_frame = start_frame
        if max_frame is None:
            max_frame = end_frame

        cmds.playbackOptions(
            minTime=start_frame,
            maxTime=end_frame,
            animationStartTime=min_frame,
            animationEndTime=max_frame,
        )
        return success_result(
            "Timeline set: {} - {}".format(start_frame, end_frame),
            start_frame=start_frame,
            end_frame=end_frame,
            min_frame=min_frame,
            max_frame=max_frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_timeline failed")
        return error_result("Failed to set timeline", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_timeline`."""
    return set_timeline(**kwargs)


if __name__ == "__main__":
    import json

    result = set_timeline()
    print(json.dumps(result))
