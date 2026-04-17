"""Duplicate an object in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def duplicate_object(
    object_name: str,
    new_name: Optional[str] = None,
    instance: bool = False,
) -> dict:
    """Duplicate an object in the Maya scene.

    Args:
        object_name: Name of the object to duplicate.
        new_name: Optional name for the duplicated object.
        instance: If True, create an instance instead of a full copy.

    Returns:
        ToolResult dict with ``context.object_name`` of the new object.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        result = cmds.duplicate(object_name, instanceLeaf=instance, returnRootsOnly=True)
        new_obj = result[0]
        if new_name:
            new_obj = cmds.rename(new_obj, new_name)

        return skill_success(
            "Duplicated '{}' as '{}'".format(object_name, new_obj),
            object_name=new_obj,
            source=object_name,
            instance=instance,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to duplicate '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`duplicate_object`."""
    return duplicate_object(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
