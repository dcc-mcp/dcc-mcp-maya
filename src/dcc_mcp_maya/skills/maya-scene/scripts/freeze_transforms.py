"""Freeze (apply) the transforms of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def freeze_transforms(object_name: str) -> dict:
    """Freeze (apply) the transforms of an object.

    Zeroes out translate/rotate and sets scale to 1 by baking current
    transform values into the shape.

    Args:
        object_name: Name of the object whose transforms to freeze.

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

        cmds.makeIdentity(object_name, apply=True, translate=True, rotate=True, scale=True)
        return maya_success(
            "Transforms frozen on '{}'".format(object_name),
            object_name=object_name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to freeze transforms on '{}'".format(object_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`freeze_transforms`."""
    return freeze_transforms(**kwargs)

if __name__ == "__main__":
    import json

    result = freeze_transforms()
    print(json.dumps(result))
