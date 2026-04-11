"""Group a list of objects under a new group node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def group_objects(objects: List[str], group_name: Optional[str] = None, world: bool = False) -> dict:
    """Group a list of objects under a new group node.

    Args:
        objects: List of object names to group.
        group_name: Optional name for the new group node.
        world: If True, the group is parented to the world (root level).

    Returns:
        ActionResultModel dict with ``context.group_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return maya_error("No objects provided", "objects list must not be empty")

        existing = cmds.ls(objects) or []
        if not existing:
            return maya_error(
                "No objects found",
                "None of the requested objects exist: {}".format(objects),
            )

        kwargs = {}  # type: dict
        if world:
            kwargs["world"] = True
        grp = cmds.group(existing, **kwargs)
        if group_name:
            grp = cmds.rename(grp, group_name)

        return maya_success(
            "Grouped {} object(s) into '{}'".format(len(existing), grp),
            group_name=grp,
            objects=existing,
            count=len(existing),
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to group objects")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`group_objects`."""
    return group_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = group_objects()
    print(json.dumps(result))
