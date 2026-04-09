"""Merge coincident vertices on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def merge_vertices(
    object_name: str,
    threshold: float = 0.001,
) -> dict:
    """Merge coincident vertices on a polygon mesh.

    Args:
        object_name: Transform or mesh name.
        threshold: Distance threshold for merging.  Default: 0.001.

    Returns:
        ActionResultModel dict with ``context.merged_count`` (approximate).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        before = cmds.polyEvaluate(object_name, vertex=True)
        cmds.polyMergeVertex(object_name, distance=threshold, ch=False)
        after = cmds.polyEvaluate(object_name, vertex=True)

        before_count = before if isinstance(before, int) else 0
        after_count = after if isinstance(after, int) else 0
        merged = before_count - after_count

        return success_result(
            "Merged {} vertices on '{}' (threshold={})".format(merged, object_name, threshold),
            object_name=object_name,
            merged_count=merged,
            vertex_count_before=before_count,
            vertex_count_after=after_count,
            threshold=threshold,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("merge_vertices failed")
        return error_result("Failed to merge vertices", str(exc)).to_dict()


def main(**kwargs):
    return merge_vertices(**kwargs)


if __name__ == "__main__":
    import json

    result = merge_vertices()
    print(json.dumps(result))
