"""Freeze (apply) the transforms of an object."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


def freeze_transforms(object_name: str) -> dict:
    """Freeze (apply) the transforms of an object.

    Zeroes out translate/rotate and sets scale to 1 by baking current
    transform values into the shape.

    Args:
        object_name: Name of the object whose transforms to freeze.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        cmds.makeIdentity(object_name, apply=True, translate=True, rotate=True, scale=True)
        return skill_success(
            "Transforms frozen on '{}'".format(object_name),
            object_name=object_name,
            prompt="Check the result with list_scene or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to freeze transforms on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`freeze_transforms`."""
    return freeze_transforms(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
