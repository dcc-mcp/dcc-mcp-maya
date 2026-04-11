"""Get translate/rotate/scale of an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def get_transform(object_name: str) -> dict:
    """Get the translate/rotate/scale of an object.

    Args:
        object_name: Name of the object to query.

    Returns:
        ActionResultModel dict with translate, rotate, scale lists.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        translate = list(cmds.getAttr("{}.translate".format(object_name))[0])
        rotate = list(cmds.getAttr("{}.rotate".format(object_name))[0])
        scale = list(cmds.getAttr("{}.scale".format(object_name))[0])
        return maya_success(
            "Transform of {}".format(object_name),
            object_name=object_name,
            translate=translate,
            rotate=rotate,
            scale=scale,
            prompt="Check the result with list_primitives or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get transform of {}".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_transform`."""
    return get_transform(**kwargs)


if __name__ == "__main__":
    import json

    result = get_transform()
    print(json.dumps(result))
