"""Show or hide an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        cmds.setAttr("{}.visibility".format(object_name), 1 if visible else 0)
        state = "visible" if visible else "hidden"
        return maya_success(
            "'{}' is now {}".format(object_name, state),
            object_name=object_name,
            visible=visible,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set visibility on '{}'".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_visibility`."""
    return set_visibility(**kwargs)


if __name__ == "__main__":
    import json

    result = set_visibility()
    print(json.dumps(result))
