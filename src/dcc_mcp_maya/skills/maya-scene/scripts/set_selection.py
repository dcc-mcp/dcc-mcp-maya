"""Set the active Maya selection."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List


def set_selection(objects: List[str]) -> dict:
    """Set the active Maya selection.

    Args:
        objects: List of object names to select.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        cmds.select(objects, replace=True)
        return maya_success(
            f"Selected {len(objects)} objects",
            selection=objects,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set selection")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_selection`."""
    return set_selection(**kwargs)


if __name__ == "__main__":
    import json

    result = set_selection()
    print(json.dumps(result))
