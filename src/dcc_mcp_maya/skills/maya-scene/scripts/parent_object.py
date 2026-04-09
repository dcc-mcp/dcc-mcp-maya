"""Set or clear the parent of an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(child):
            return error_result(
                "Child not found: {}".format(child),
                "'{}' does not exist in the scene".format(child),
            ).to_dict()

        if world or parent is None:
            cmds.parent(child, world=True)
            return success_result(
                "Parented '{}' to world".format(child),
                child=child,
                parent=None,
            ).to_dict()

        if not cmds.objExists(parent):
            return error_result(
                "Parent not found: {}".format(parent),
                "'{}' does not exist in the scene".format(parent),
            ).to_dict()

        cmds.parent(child, parent)
        return success_result(
            "Parented '{}' under '{}'".format(child, parent),
            child=child,
            parent=parent,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("parent_object failed")
        return error_result("Failed to parent '{}'".format(child), str(exc)).to_dict()


def main(**kwargs):
    return parent_object(**kwargs)


if __name__ == "__main__":
    import json

    result = parent_object()
    print(json.dumps(result))
