"""Add objects to an existing Maya object set."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists


def add_to_set(
    set_name: str,
    objects: List[str],
) -> dict:
    """Add objects to an existing Maya object set.

    Args:
        set_name: Name of an existing ``objectSet`` node.
        objects: List of object names to add.

    Returns:
        ToolResult dict with ``context.set_name`` and
        ``context.objects_added``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return skill_error("No objects specified", "objects list must not be empty")

        err = validate_node_exists(cmds, set_name)
        if err:
            return err

        if cmds.objectType(set_name) != "objectSet":
            return skill_error(
                "Not an object set: {}".format(set_name),
                "'{}' is of type '{}', expected 'objectSet'".format(set_name, cmds.objectType(set_name)),
            )

        err = batch_validate_nodes(cmds, list(objects))
        if err:
            return err

        cmds.sets(*objects, addElement=set_name)

        return skill_success(
            "Added {} object(s) to set '{}'".format(len(objects), set_name),
            set_name=set_name,
            objects_added=list(objects),
            prompt="Use list_set_members to verify membership.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add objects to set '{}'".format(set_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_to_set`."""
    return add_to_set(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
