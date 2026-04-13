"""Query the world-space bounding box of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import bounding_box_from_node, validate_node_exists


def get_bounding_box(object_name: str) -> dict:
    """Query the world-space bounding box of an object.

    Uses :func:`dcc_mcp_maya.api.bounding_box_from_node` to produce
    a ``BoundingBox``-compatible dict for cross-DCC exchange.

    Args:
        object_name: Name of the object to query.

    Returns:
        ActionResultModel dict with ``context.min``, ``context.max``,
        ``context.center``, and ``context.size``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        bb = bounding_box_from_node(cmds, object_name)
        return skill_success(
            "Bounding box of '{}'".format(object_name),
            object_name=object_name,
            bounding_box=bb,
            **bb,
            prompt="Use get_transform for position or set_transform to move the object.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get bounding box of '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_bounding_box`."""
    return get_bounding_box(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
