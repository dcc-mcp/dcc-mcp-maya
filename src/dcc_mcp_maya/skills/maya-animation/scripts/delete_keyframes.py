"""Delete keyframes from an object within an optional frame range."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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
        return skill_success(
            "Deleted {} keyframe(s) from {}".format(deleted, object_name),
            object_name=object_name,
            deleted_count=deleted,
            attributes=attributes,
            start_frame=start_frame,
            end_frame=end_frame,
            prompt="Use set_keyframe to add new keys, or get_keyframes to verify the result.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete keyframes from {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_keyframes`."""
    return delete_keyframes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
