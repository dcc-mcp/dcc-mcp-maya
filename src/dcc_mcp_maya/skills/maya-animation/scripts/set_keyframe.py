"""Set a keyframe on an object at the given time."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def set_keyframe(
    object_name: str,
    attributes: Optional[List[str]] = None,
    time: Optional[float] = None,
    value: Optional[float] = None,
) -> dict:
    """Set a keyframe on an object at the given time.

    Args:
        object_name: Name of the object to keyframe.
        attributes: List of attribute names to key (e.g. ``["tx", "ty", "tz"]``).
            If None, keys all keyable attributes.
        time: Frame number.  Defaults to current time.
        value: Explicit value to set before keying.  Only valid when a single
            attribute is provided.

    Returns:
        ActionResultModel dict with ``context.keyframe_count``.
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
        if time is not None:
            kwargs["time"] = time
        if attributes:
            kwargs["attribute"] = attributes
            if value is not None and len(attributes) == 1:
                cmds.setAttr("{}.{}".format(object_name, attributes[0]), value)

        count = cmds.setKeyframe(object_name, **kwargs)
        return success_result(
            "Set {} keyframe(s) on {}".format(count, object_name),
            object_name=object_name,
            keyframe_count=count,
            time=time,
            attributes=attributes,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_keyframe failed")
        return error_result("Failed to set keyframe on {}".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return set_keyframe(**kwargs)


if __name__ == "__main__":
    import json

    result = set_keyframe()
    print(json.dumps(result))
