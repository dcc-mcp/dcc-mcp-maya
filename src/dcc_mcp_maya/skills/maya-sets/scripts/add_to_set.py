"""Add objects to an existing Maya object set."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


def add_to_set(
    set_name: str,
    objects: List[str],
) -> dict:
    """Add objects to an existing Maya object set.

    Args:
        set_name: Name of an existing ``objectSet`` node.
        objects: List of object names to add.

    Returns:
        ActionResultModel dict with ``context.set_name`` and
        ``context.objects_added``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return error_result("No objects specified", "objects list must not be empty").to_dict()

        if not cmds.objExists(set_name):
            return error_result(
                "Set not found: {}".format(set_name),
                "'{}' does not exist in the scene".format(set_name),
            ).to_dict()

        if cmds.objectType(set_name) != "objectSet":
            return error_result(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            ).to_dict()

        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            ).to_dict()

        cmds.sets(*objects, addElement=set_name)

        return success_result(
            "Added {} object(s) to set '{}'".format(len(objects), set_name),
            set_name=set_name,
            objects_added=list(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_to_set failed")
        return error_result("Failed to add objects to set '{}'".format(set_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_to_set`."""
    return add_to_set(**kwargs)


if __name__ == "__main__":
    import json

    result = add_to_set()
    print(json.dumps(result))
