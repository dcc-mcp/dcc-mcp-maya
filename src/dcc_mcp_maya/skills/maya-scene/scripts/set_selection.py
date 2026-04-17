"""Set the active Maya selection."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def set_selection(objects: List[str]) -> dict:
    """Set the active Maya selection.

    Args:
        objects: List of object names to select.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.select(objects, replace=True)
        return skill_success(
            f"Selected {len(objects)} objects",
            selection=objects,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set selection")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_selection`."""
    return set_selection(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
