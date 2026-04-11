"""Duplicate an object in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, validate_node_exists


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
        ActionResultModel dict with ``context.object_name`` of the new object.
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

        return maya_success(
            "Duplicated '{}' as '{}'".format(object_name, new_obj),
            object_name=new_obj,
            source=object_name,
            instance=instance,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to duplicate '{}'".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`duplicate_object`."""
    return duplicate_object(**kwargs)


if __name__ == "__main__":
    import json

    result = duplicate_object()
    print(json.dumps(result))
