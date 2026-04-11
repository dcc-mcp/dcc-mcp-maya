"""Lock or unlock the transform attributes of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def lock_object(object_name: str, lock: bool = True) -> dict:
    """Lock or unlock the transform attributes of an object.

    When locked, translate/rotate/scale channels cannot be edited.

    Args:
        object_name: Name of the object.
        lock: True to lock, False to unlock.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

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
        return maya_success(
            "Transform attributes {} on '{}'".format(state, object_name),
            object_name=object_name,
            locked=lock,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to {} '{}'".format("lock" if lock else "unlock", object_name))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`lock_object`."""
    return lock_object(**kwargs)

if __name__ == "__main__":
    import json

    result = lock_object()
    print(json.dumps(result))
