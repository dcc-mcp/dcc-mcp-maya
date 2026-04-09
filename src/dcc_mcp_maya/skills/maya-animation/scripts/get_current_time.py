"""Get the current frame number."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_current_time() -> dict:
    """Get the current frame number.

    Returns:
        ActionResultModel dict with ``context.current_time``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        current = cmds.currentTime(query=True)
        return success_result(
            "Current time: {}".format(current),
            current_time=current,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_current_time failed")
        return error_result("Failed to get current time", str(exc)).to_dict()


def main(**kwargs):
    return get_current_time(**kwargs)


if __name__ == "__main__":
    import json

    result = get_current_time()
    print(json.dumps(result))
