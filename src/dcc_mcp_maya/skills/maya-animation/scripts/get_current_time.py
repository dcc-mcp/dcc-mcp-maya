"""Get the current frame number."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def get_current_time() -> dict:
    """Get the current frame number.

    Returns:
        ActionResultModel dict with ``context.current_time``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        current = cmds.currentTime(query=True)
        return maya_success(
            "Current time: {}".format(current),
            current_time=current,
            prompt="Use set_current_time to seek to a specific frame.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get current time")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_current_time`."""
    return get_current_time(**kwargs)


if __name__ == "__main__":
    import json

    result = get_current_time()
    print(json.dumps(result))
