"""Create a Maya object set."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not name or not name.strip():
            return error_result("Invalid set name", "name must not be empty").to_dict()

        objects_to_add = list(objects) if objects else []
        missing = [obj for obj in objects_to_add if not cmds.objExists(obj)]
        if missing:
            return error_result(
                "Objects not found: {}".format(missing),
                "The following objects do not exist: {}".format(missing),
            ).to_dict()

        if objects_to_add:
            set_node = cmds.sets(*objects_to_add, name=name)
        else:
            set_node = cmds.sets(name=name, empty=True)

        return success_result(
            "Created object set '{}' with {} object(s)".format(set_node, len(objects_to_add)),
            set_name=set_node,
            objects_added=objects_to_add,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_set failed")
        return error_result("Failed to create set '{}'".format(name), str(exc)).to_dict()


def main(**kwargs):
    return create_set(**kwargs)


if __name__ == "__main__":
    import json

    result = create_set()
    print(json.dumps(result))
