"""Set or clear the parent of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional


def parent_object(child: str, parent: Optional[str] = None, world: bool = False) -> dict:
    """Set or clear the parent of an object.

    Args:
        child: Name of the object to re-parent.
        parent: Name of the new parent.  If None and *world* is True, the
            object is parented to the world (un-parented).
        world: If True, parent the object to the world regardless of *parent*.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(child):
            return maya_error(
                "Child not found: {}".format(child),
                "'{}' does not exist in the scene".format(child),
            )

        if world or parent is None:
            cmds.parent(child, world=True)
            return maya_success(
                "Parented '{}' to world".format(child),
                child=child,
                parent=None,
                prompt="Check the result with list_scene or use related actions to continue.",
            )

        if not cmds.objExists(parent):
            return maya_error(
                "Parent not found: {}".format(parent),
                "'{}' does not exist in the scene".format(parent),
            )

        cmds.parent(child, parent)
        return maya_success(
            "Parented '{}' under '{}'".format(child, parent),
            child=child,
            parent=parent,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to parent '{}'".format(child))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`parent_object`."""
    return parent_object(**kwargs)


if __name__ == "__main__":
    import json

    result = parent_object()
    print(json.dumps(result))
