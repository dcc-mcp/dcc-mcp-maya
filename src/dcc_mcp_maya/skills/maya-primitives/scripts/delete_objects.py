"""Delete objects from the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


def delete_objects(objects: List[str]) -> dict:
    """Delete objects from the Maya scene.

    Args:
        objects: List of object names to delete.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not objects:
            return success_result("No objects to delete").to_dict()
        existing = cmds.ls(objects) or []
        if existing:
            cmds.delete(existing)
        return success_result(
            f"Deleted {len(existing)} objects",
            deleted=existing,
            requested=objects,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_objects failed")
        return error_result("Failed to delete objects", str(exc)).to_dict()


def main(**kwargs):
    return delete_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_objects()
    print(json.dumps(result))
