"""Center the pivot point of an object to its bounding box center."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def center_pivot(object_name: str) -> dict:
    """Center the pivot point of an object to its bounding box center.

    Args:
        object_name: Name of the object.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        cmds.xform(object_name, centerPivots=True)
        pivot = list(cmds.xform(object_name, query=True, worldSpace=True, pivots=True))
        return skill_success(
            "Pivot centered on '{}'".format(object_name),
            object_name=object_name,
            pivot=pivot,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to center pivot on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`center_pivot`."""
    return center_pivot(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
