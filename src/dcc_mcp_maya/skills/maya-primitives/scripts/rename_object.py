"""Rename an object in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        result = cmds.rename(object_name, new_name)
        return maya_success(
            "Renamed '{}' to '{}'".format(object_name, result),
            old_name=object_name,
            object_name=result,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to rename {}".format(object_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`rename_object`."""
    return rename_object(**kwargs)

if __name__ == "__main__":
    import json

    result = rename_object()
    print(json.dumps(result))
