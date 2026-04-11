"""Delete keyframes from an object within an optional frame range."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

def delete_keyframes(
    object_name: str,
    attributes: Optional[List[str]] = None,
    start_frame: Optional[float] = None,
    end_frame: Optional[float] = None,
) -> dict:
    """Delete keyframes from an object within an optional frame range.

    Args:
        object_name: Name of the object whose keyframes will be deleted.
        attributes: List of attribute names to affect (e.g. ``["tx", "ry"]``).
            If None, all keyable attributes are targeted.
        start_frame: First frame of the range to delete.  If None and
            *end_frame* is also None, all keyframes are deleted.
        end_frame: Last frame of the range to delete.  If None and
            *start_frame* is also None, all keyframes are deleted.

    Returns:
        ActionResultModel dict with ``context.deleted_count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        kwargs = {}  # type: Dict
        if attributes:
            kwargs["attribute"] = attributes
        if start_frame is not None and end_frame is not None:
            kwargs["time"] = (start_frame, end_frame)
        elif start_frame is not None:
            kwargs["time"] = (start_frame, start_frame)
        elif end_frame is not None:
            kwargs["time"] = (end_frame, end_frame)

        deleted = cmds.cutKey(object_name, clear=True, **kwargs)
        return maya_success(
            "Deleted {} keyframe(s) from {}".format(deleted, object_name),
            object_name=object_name,
            deleted_count=deleted,
            attributes=attributes,
            start_frame=start_frame,
            end_frame=end_frame,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete keyframes from {}".format(object_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_keyframes`."""
    return delete_keyframes(**kwargs)

if __name__ == "__main__":
    import json

    result = delete_keyframes()
    print(json.dumps(result))
