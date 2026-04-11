"""Rename an object in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def rename_object(object_name: str, new_name: str) -> dict:
    """Rename a Maya object.

    Args:
        object_name: Current name of the object.
        new_name: New name to assign.

    Returns:
        ActionResultModel dict with ``context.object_name`` (new name).
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        result = cmds.rename(object_name, new_name)
        return skill_success(
            "Renamed '{}' to '{}'".format(object_name, result),
            old_name=object_name,
            object_name=result,
            prompt="Check the result with list_primitives or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to rename {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`rename_object`."""
    return rename_object(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
