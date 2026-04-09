"""Create a new vertex color set on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    valid_reps = ("RGB", "RGBA")
    if representation not in valid_reps:
        return error_result(
            "Invalid representation: {}".format(representation),
            "Use one of: {}".format(", ".join(valid_reps)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        existing = cmds.polyColorSet(object_name, query=True, allColorSets=True) or []
        if color_set_name in existing:
            return error_result("Color set '{}' already exists on '{}'".format(color_set_name, object_name)).to_dict()

        cmds.polyColorSet(
            object_name,
            create=True,
            colorSet=color_set_name,
            representation=representation,
        )

        return success_result(
            "Created color set '{}' on '{}'".format(color_set_name, object_name),
            object_name=object_name,
            color_set_name=color_set_name,
            representation=representation,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_color_set failed")
        return error_result("Failed to create color set", str(exc)).to_dict()


def main(**kwargs):
    return create_color_set(**kwargs)


if __name__ == "__main__":
    import json

    result = create_color_set()
    print(json.dumps(result))
