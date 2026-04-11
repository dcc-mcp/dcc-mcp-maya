"""Create a new vertex color set on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules


def create_color_set(
    object_name: str,
    color_set_name: str,
    representation: str = "RGBA",
) -> dict:
    """Create a new vertex color set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        color_set_name: Name for the new color set.
        representation: Color representation — ``"RGB"`` or ``"RGBA"``.
            Default: ``"RGBA"``.

    Returns:
        ActionResultModel dict.
    """

    valid_reps = ("RGB", "RGBA")
    if representation not in valid_reps:
        return maya_error(
            "Invalid representation: {}".format(representation),
            "Use one of: {}".format(", ".join(valid_reps)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error("Object not found: {}".format(object_name))

        existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
        if color_set_name in existing:
            return maya_error("Color set '{}' already exists on '{}'".format(color_set_name, object_name))

        cmds.polyColorSet(
            object_name,
            create=True,
            colorSet=color_set_name,
            representation=representation,
        )

        return maya_success(
            "Created color set '{}' on '{}'".format(color_set_name, object_name),
            object_name=object_name,
            color_set_name=color_set_name,
            representation=representation,
            prompt="Check the result with list_vertex_color or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create color set")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_color_set`."""
    return create_color_set(**kwargs)


if __name__ == "__main__":
    import json

    result = create_color_set()
    print(json.dumps(result))
