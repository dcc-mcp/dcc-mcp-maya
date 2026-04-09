"""Set the current frame number."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_current_time(frame: float) -> dict:
    """Set the current frame number.

    Args:
        frame: Target frame number.

    Returns:
        ActionResultModel dict with ``context.current_time``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.currentTime(frame, update=True)
        return success_result(
            "Current time set to {}".format(frame),
            current_time=frame,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_current_time failed")
        return error_result("Failed to set current time", str(exc)).to_dict()


def main(**kwargs):
    return set_current_time(**kwargs)


if __name__ == "__main__":
    import json

    result = set_current_time()
    print(json.dumps(result))
