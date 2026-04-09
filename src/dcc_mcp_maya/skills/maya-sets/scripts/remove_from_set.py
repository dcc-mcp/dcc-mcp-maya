"""Remove objects from an existing Maya object set."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


def remove_from_set(
    set_name: str,
    objects: List[str],
) -> dict:
    """Remove objects from an existing Maya object set.

    Args:
        set_name: Name of an existing ``objectSet`` node.
        objects: List of object names to remove.

    Returns:
        ActionResultModel dict with ``context.set_name`` and
        ``context.objects_removed``.
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

        # Only attempt to remove objects that actually exist
        existing = [obj for obj in objects if cmds.objExists(obj)]
        if existing:
            cmds.sets(*existing, remove=set_name)

        removed_count = len(existing)
        skipped = [obj for obj in objects if obj not in existing]

        return success_result(
            "Removed {} object(s) from set '{}'{}".format(
                removed_count,
                set_name,
                " ({} not found, skipped)".format(len(skipped)) if skipped else "",
            ),
            set_name=set_name,
            objects_removed=existing,
            objects_skipped=skipped,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_from_set failed")
        return error_result("Failed to remove objects from set '{}'".format(set_name), str(exc)).to_dict()


def main(**kwargs):
    return remove_from_set(**kwargs)


if __name__ == "__main__":
    import json

    result = remove_from_set()
    print(json.dumps(result))
