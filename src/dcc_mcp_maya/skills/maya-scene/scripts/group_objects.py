"""Group a list of objects under a new group node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def group_objects(objects: List[str], group_name: Optional[str] = None, world: bool = False) -> dict:
    """Group a list of objects under a new group node.

    Args:
        objects: List of object names to group.
        group_name: Optional name for the new group node.
        world: If True, the group is parented to the world (root level).

    Returns:
        ActionResultModel dict with ``context.group_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return error_result("No objects provided", "objects list must not be empty").to_dict()

        existing = cmds.ls(objects) or []
        if not existing:
            return error_result(
                "No objects found",
                "None of the requested objects exist: {}".format(objects),
            ).to_dict()

        kwargs = {}  # type: dict
        if world:
            kwargs["world"] = True
        grp = cmds.group(existing, **kwargs)
        if group_name:
            grp = cmds.rename(grp, group_name)

        return success_result(
            "Grouped {} object(s) into '{}'".format(len(existing), grp),
            group_name=grp,
            objects=existing,
            count=len(existing),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("group_objects failed")
        return error_result("Failed to group objects", str(exc)).to_dict()


def main(**kwargs):
    return group_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = group_objects()
    print(json.dumps(result))
