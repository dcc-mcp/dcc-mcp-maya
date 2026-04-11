"""Create a Maya object set."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional


def create_set(
    name: str,
    objects: Optional[List[str]] = None,
) -> dict:
    """Create a Maya object set.

    Args:
        name: Name for the new object set.
        objects: Optional list of objects to add immediately.
            If None or empty, an empty set is created.

    Returns:
        ActionResultModel dict with ``context.set_name`` and
        ``context.objects_added``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not name.strip():
            return maya_error("Invalid set name", "name must not be empty")

        objects_to_add = list(objects) if objects else []
        missing = [obj for obj in objects_to_add if not cmds.objExists(obj)]
        if missing:
            return maya_error(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            )

        if objects_to_add:
            set_node = cmds.sets(*objects_to_add, name=name)
        else:
            set_node = cmds.sets(name=name, empty=True)

        return maya_success(
            "Created object set '{}' with {} object(s)".format(set_node, len(objects_to_add)),
            set_name=set_node,
            objects_added=objects_to_add,
            prompt="Use add_to_set to populate or list_sets to review.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create set '{}'".format(name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_set`."""
    return create_set(**kwargs)


if __name__ == "__main__":
    import json

    result = create_set()
    print(json.dumps(result))
