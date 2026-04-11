"""Show or hide an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def set_visibility(object_name: str, visible: bool) -> dict:
    """Show or hide an object.

    Args:
        object_name: Name of the object to show/hide.
        visible: True to show, False to hide.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        cmds.setAttr("{}.visibility".format(object_name), 1 if visible else 0)
        state = "visible" if visible else "hidden"
        return skill_success(
            "'{}' is now {}".format(object_name, state),
            object_name=object_name,
            visible=visible,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set visibility on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_visibility`."""
    return set_visibility(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
