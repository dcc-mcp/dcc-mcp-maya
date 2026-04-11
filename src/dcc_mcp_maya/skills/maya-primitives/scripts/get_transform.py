"""Get translate/rotate/scale of an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def get_transform(object_name: str) -> dict:
    """Get the translate/rotate/scale of an object.

    Args:
        object_name: Name of the object to query.

    Returns:
        ActionResultModel dict with translate, rotate, scale lists.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        translate = list(cmds.getAttr("{}.translate".format(object_name))[0])
        rotate = list(cmds.getAttr("{}.rotate".format(object_name))[0])
        scale = list(cmds.getAttr("{}.scale".format(object_name))[0])
        return skill_success(
            "Transform of {}".format(object_name),
            object_name=object_name,
            translate=translate,
            rotate=rotate,
            scale=scale,
            prompt="Check the result with list_primitives or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get transform of {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_transform`."""
    return get_transform(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
