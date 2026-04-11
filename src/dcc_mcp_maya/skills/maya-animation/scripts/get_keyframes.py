"""Get all keyframe times for an object / attribute."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        kwargs = {}  # type: Dict
        if attribute:
            kwargs["attribute"] = attribute
        raw = cmds.keyframe(object_name, query=True, timeChange=True, **kwargs)
        keyframes = list(raw) if raw else []
        return success_result(
            "Found {} keyframe(s) on {}".format(len(keyframes), object_name),
            object_name=object_name,
            attribute=attribute,
            keyframes=keyframes,
            count=len(keyframes),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_keyframes failed")
        return error_result("Failed to get keyframes for {}".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_keyframes`."""
    return get_keyframes(**kwargs)


if __name__ == "__main__":
    import json

    result = get_keyframes()
    print(json.dumps(result))
