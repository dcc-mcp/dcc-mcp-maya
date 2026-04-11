"""Add objects to an existing Maya object set."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List


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

        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return maya_error(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            )

        cmds.sets(*objects, addElement=set_name)

        return maya_success(
            "Added {} object(s) to set '{}'".format(len(objects), set_name),
            set_name=set_name,
            objects_added=list(objects),
            prompt="Use list_set_members to verify membership.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add objects to set '{}'".format(set_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_to_set`."""
    return add_to_set(**kwargs)


if __name__ == "__main__":
    import json

    result = add_to_set()
    print(json.dumps(result))
