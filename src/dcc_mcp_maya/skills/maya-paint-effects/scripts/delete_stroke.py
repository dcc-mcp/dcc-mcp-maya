"""Delete a Maya Paint Effects stroke node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_stroke(name: str, delete_transform: bool = True) -> dict:
    """Delete a Paint Effects stroke node (and optionally its transform).

    Args:
        name: Name of the stroke node or its transform to delete.
        delete_transform: If True (default), delete the transform parent as well.

    Returns:
        ActionResultModel dict indicating success or failure.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not name:
        return error_result(
            "Missing required parameter 'name'",
            "Provide the stroke node or transform name.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(name):
            return error_result(
                "Node '{}' not found".format(name),
                "Use list_strokes to find valid stroke names.",
            ).to_dict()

        node_type = cmds.objectType(name)
        deleted = []

        if node_type == "stroke" and delete_transform:
            transform = cmds.listRelatives(name, parent=True, fullPath=False)
            target = transform[0] if transform else name
        else:
            target = name

        cmds.delete(target)
        deleted.append(target)

        return success_result(
            "Deleted stroke '{}'".format(name),
            prompt="Stroke deleted. Use create_stroke to add a new one.",
            deleted=deleted,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_stroke failed")
        return error_result("Failed to delete stroke", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_stroke(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_stroke(name="stroke1")))
