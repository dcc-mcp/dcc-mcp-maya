"""Lock or unlock the transform attributes of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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
        return skill_success(
            "Transform attributes {} on '{}'".format(state, object_name),
            object_name=object_name,
            locked=lock,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to {} '{}'".format("lock" if lock else "unlock", object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`lock_object`."""
    return lock_object(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
