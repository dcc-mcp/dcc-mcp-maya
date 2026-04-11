"""Set a keyframe on an object at the given time."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_keyframe(
    object_name: str,
    attribute: Optional[str] = None,
    attributes: Optional[List[str]] = None,
    time: Optional[float] = None,
    value: Optional[float] = None,
) -> dict:
    """Set a keyframe on an object at the given time.

    Args:
        object_name: Name of the object to keyframe.
        attribute: Single attribute name to key (e.g. ``"translateX"``).  Takes
            priority over ``attributes`` when both are provided.
        attributes: List of attribute names to key.  Ignored when ``attribute``
            is set.
        time: Frame number.  Defaults to current time.
        value: Explicit value to set before keying.  Only valid for a single
            attribute.

    Returns:
        ActionResultModel dict with ``context.keyframe_count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        kwargs = {}
        # Normalise: single `attribute` string takes priority over `attributes` list
        attr_list = [attribute] if attribute else (attributes or [])
        if time is not None:
            kwargs["time"] = time
        if attr_list:
            kwargs["attribute"] = attr_list
            if value is not None and len(attr_list) == 1:
                cmds.setAttr("{}.{}".format(object_name, attr_list[0]), value)

        count = cmds.setKeyframe(object_name, **kwargs)
        return skill_success(
            "Set {} keyframe(s) on {}".format(count, object_name),
            object_name=object_name,
            keyframe_count=count,
            time=time,
            attributes=attr_list,
            prompt="Use get_keyframes to verify or bake_simulation to collapse to keys.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set keyframe on {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_keyframe`."""
    return set_keyframe(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
