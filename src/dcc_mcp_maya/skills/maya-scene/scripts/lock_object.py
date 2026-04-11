"""Lock or unlock the transform attributes of an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def lock_object(object_name: str, lock: bool = True) -> dict:
    """Lock or unlock the transform attributes of an object.

    When locked, translate/rotate/scale channels cannot be edited.

    Args:
        object_name: Name of the object.
        lock: True to lock, False to unlock.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        _LOCK_ATTRS = [
            "translateX",
            "translateY",
            "translateZ",
            "rotateX",
            "rotateY",
            "rotateZ",
            "scaleX",
            "scaleY",
            "scaleZ",
        ]
        for attr in _LOCK_ATTRS:
            cmds.setAttr("{}.{}".format(object_name, attr), lock=lock)

        state = "locked" if lock else "unlocked"
        return success_result(
            "Transform attributes {} on '{}'".format(state, object_name),
            object_name=object_name,
            locked=lock,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("lock_object failed")
        return error_result("Failed to {} '{}'".format("lock" if lock else "unlock", object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`lock_object`."""
    return lock_object(**kwargs)


if __name__ == "__main__":
    import json

    result = lock_object()
    print(json.dumps(result))
