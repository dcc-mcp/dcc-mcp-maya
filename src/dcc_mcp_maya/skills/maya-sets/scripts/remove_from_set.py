"""Remove objects from an existing Maya object set."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List

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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return maya_error("No objects specified", "objects list must not be empty")

        if not cmds.objExists(set_name):
            return maya_error(
                "Set not found: {}".format(set_name),
                "'{}' does not exist in the scene".format(set_name),
            )

        if cmds.objectType(set_name) != "objectSet":
            return maya_error(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            )

        # Only attempt to remove objects that actually exist
        existing = [obj for obj in objects if cmds.objExists(obj)]
        if existing:
            cmds.sets(*existing, remove=set_name)

        removed_count = len(existing)
        skipped = [obj for obj in objects if obj not in existing]

        return maya_success(
            "Removed {} object(s) from set '{}'{}".format(
                removed_count,
                set_name,
                " ({} not found, skipped)".format(len(skipped)) if skipped else "",
            ),
            set_name=set_name,
            objects_removed=existing,
            objects_skipped=skipped,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to remove objects from set '{}'".format(set_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_from_set`."""
    return remove_from_set(**kwargs)

if __name__ == "__main__":
    import json

    result = remove_from_set()
    print(json.dumps(result))
