"""Merge coincident vertices on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error("Object not found: {}".format(object_name), "")

        before = cmds.polyEvaluate(object_name, vertex=True)
        cmds.polyMergeVertex(object_name, distance=threshold, ch=False)
        after = cmds.polyEvaluate(object_name, vertex=True)

        before_count = before if isinstance(before, int) else 0
        after_count = after if isinstance(after, int) else 0
        merged = before_count - after_count

        return maya_success(
            "Merged {} vertices on '{}' (threshold={})".format(merged, object_name, threshold),
            object_name=object_name,
            merged_count=merged,
            vertex_count_before=before_count,
            vertex_count_after=after_count,
            threshold=threshold,
            prompt="Use cleanup_mesh to verify or get_poly_count to check the result.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to merge vertices")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`merge_vertices`."""
    return merge_vertices(**kwargs)


if __name__ == "__main__":
    import json

    result = merge_vertices()
    print(json.dumps(result))
