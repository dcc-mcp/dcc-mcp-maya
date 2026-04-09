"""Triangulate all faces of a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def triangulate(object_name: str) -> dict:
    """Triangulate all faces of a polygon mesh.

    Args:
        object_name: Transform or mesh name.

    Returns:
        ActionResultModel dict with face counts before and after.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        before = cmds.polyEvaluate(object_name, face=True)
        cmds.polyTriangulate(object_name)
        after = cmds.polyEvaluate(object_name, face=True)

        before_count = before if isinstance(before, int) else 0
        after_count = after if isinstance(after, int) else 0

        return success_result(
            "Triangulated '{}': {} -> {} faces".format(object_name, before_count, after_count),
            object_name=object_name,
            face_count_before=before_count,
            face_count_after=after_count,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("triangulate failed")
        return error_result("Failed to triangulate", str(exc)).to_dict()


def main(**kwargs):
    return triangulate(**kwargs)


if __name__ == "__main__":
    import json

    result = triangulate()
    print(json.dumps(result))
