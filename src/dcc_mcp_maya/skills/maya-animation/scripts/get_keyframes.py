"""Get all keyframe times for an object / attribute."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def get_keyframes(
    object_name: str,
    attribute: Optional[str] = None,
) -> dict:
    """Get all keyframe times for an object / attribute.

    Args:
        object_name: Name of the object to query.
        attribute: Specific attribute to query (e.g. ``"tx"``).  If None,
            returns keyframes across all attributes.

    Returns:
        ActionResultModel dict with ``context.keyframes`` list of frame numbers.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        kwargs = {}  # type: Dict
        if attribute:
            kwargs["attribute"] = attribute
        raw = cmds.keyframe(object_name, query=True, timeChange=True, **kwargs)
        keyframes = list(raw) if raw else []
        return skill_success(
            "Found {} keyframe(s) on {}".format(len(keyframes), object_name),
            object_name=object_name,
            attribute=attribute,
            keyframes=keyframes,
            count=len(keyframes),
            prompt="Use set_keyframe to modify keys or delete_keyframes to remove them.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get keyframes for {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_keyframes`."""
    return get_keyframes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
