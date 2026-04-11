"""Center the pivot point of an object to its bounding box center."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, validate_node_exists

# Import built-in modules


def center_pivot(object_name: str) -> dict:
    """Center the pivot point of an object to its bounding box center.

    Args:
        object_name: Name of the object.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        cmds.xform(object_name, centerPivots=True)
        pivot = list(cmds.xform(object_name, query=True, worldSpace=True, pivots=True))
        return maya_success(
            "Pivot centered on '{}'".format(object_name),
            object_name=object_name,
            pivot=pivot,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to center pivot on '{}'".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`center_pivot`."""
    return center_pivot(**kwargs)


if __name__ == "__main__":
    import json

    result = center_pivot()
    print(json.dumps(result))
