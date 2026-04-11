"""Create a Maya object set."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


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
            return skill_error("Invalid set name", "name must not be empty")

        objects_to_add = list(objects) if objects else []
        err = batch_validate_nodes(cmds, list(objects_to_add))
        if err:
            return err

        if objects_to_add:
            set_node = cmds.sets(*objects_to_add, name=name)
        else:
            set_node = cmds.sets(name=name, empty=True)

        return skill_success(
            "Created object set '{}' with {} object(s)".format(set_node, len(objects_to_add)),
            set_name=set_node,
            objects_added=objects_to_add,
            prompt="Use add_to_set to populate or list_sets to review.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create set '{}'".format(name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_set`."""
    return create_set(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
