"""Query the world-space bounding box of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def get_bounding_box(object_name: str) -> dict:
    """Query the world-space bounding box of an object.

    Args:
        object_name: Name of the object to query.

    Returns:
        ActionResultModel dict with ``context.min``, ``context.max``,
        ``context.center``, and ``context.size``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        bb = cmds.exactWorldBoundingBox(object_name)
        # bb = [xmin, ymin, zmin, xmax, ymax, zmax]
        bb_min = [bb[0], bb[1], bb[2]]
        bb_max = [bb[3], bb[4], bb[5]]
        center = [(bb[0] + bb[3]) / 2.0, (bb[1] + bb[4]) / 2.0, (bb[2] + bb[5]) / 2.0]
        size = [bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]]
        return maya_success(
            "Bounding box of '{}'".format(object_name),
            object_name=object_name,
            min=bb_min,
            max=bb_max,
            center=center,
            size=size,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to get bounding box of '{}'".format(object_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_bounding_box`."""
    return get_bounding_box(**kwargs)

if __name__ == "__main__":
    import json

    result = get_bounding_box()
    print(json.dumps(result))
