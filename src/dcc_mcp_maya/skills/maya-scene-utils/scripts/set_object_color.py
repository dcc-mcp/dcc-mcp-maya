"""Set the wireframe color of a Maya object by index."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def set_object_color(
    object_name: str,
    color_index: int,
    use_default: bool = False,
) -> dict:
    """Set the wireframe color of a Maya object by index.

    Maya's viewport wireframe colour can be overridden per-object using a
    colour index (0 = default/yellow, 1–31 = custom palette entries).

    Args:
        object_name: Name of the transform to colour.
        color_index: Maya colour index (0–31).  Index 0 restores the
            default colour (same as ``use_default=True``).
        use_default: When True, disable the colour override and restore the
            default wireframe colour.  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.color_index``, ``context.use_default``.
    """

    if not (0 <= color_index <= 31):
        return skill_error(
            "Invalid color_index: {}".format(color_index),
            "color_index must be between 0 and 31",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        if use_default or color_index == 0:
            cmds.setAttr("{}.overrideEnabled".format(object_name), False)
            cmds.setAttr("{}.overrideColor".format(object_name), 0)
            effective_index = 0
        else:
            cmds.setAttr("{}.overrideEnabled".format(object_name), True)
            cmds.setAttr("{}.overrideColor".format(object_name), color_index)
            effective_index = color_index

        return skill_success(
            "Set wireframe color on '{}' to index {}".format(object_name, effective_index),
            object_name=object_name,
            color_index=effective_index,
            use_default=use_default,
            prompt="Check the result with list_scene_utils or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set object color on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_object_color`."""
    return set_object_color(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
