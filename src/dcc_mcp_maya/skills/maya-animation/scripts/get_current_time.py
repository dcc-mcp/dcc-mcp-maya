"""Get the current frame number."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_current_time() -> dict:
    """Get the current frame number.

    Returns:
        ToolResult dict with ``context.current_time``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        current = cmds.currentTime(query=True)
        return skill_success(
            "Current time: {}".format(current),
            current_time=current,
            prompt="Use set_current_time to seek to a specific frame.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get current time")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_current_time`."""
    return get_current_time(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
