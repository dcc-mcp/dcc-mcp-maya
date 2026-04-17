"""Set or clear the parent of an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def parent_object(child: str, parent: Optional[str] = None, world: bool = False) -> dict:
    """Set or clear the parent of an object.

    Args:
        child: Name of the object to re-parent.
        parent: Name of the new parent.  If None and *world* is True, the
            object is parented to the world (un-parented).
        world: If True, parent the object to the world regardless of *parent*.

    Returns:
        ToolResult dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, child)
        if err:
            return err

        if world or parent is None:
            cmds.parent(child, world=True)
            return skill_success(
                "Parented '{}' to world".format(child),
                child=child,
                parent=None,
                prompt="Check the result with list_scene or use related actions to continue.",
            )

        err = validate_node_exists(cmds, parent)
        if err:
            return err

        cmds.parent(child, parent)
        return skill_success(
            "Parented '{}' under '{}'".format(child, parent),
            child=child,
            parent=parent,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to parent '{}'".format(child))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`parent_object`."""
    return parent_object(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
