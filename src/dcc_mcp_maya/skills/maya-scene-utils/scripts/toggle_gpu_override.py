"""Toggle the GPU override display mode on a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def toggle_gpu_override(
    object_name: str,
    enabled: bool = True,
) -> dict:
    """Toggle the GPU override display mode on a polygon mesh.

    Maya's GPU cache override (``gpuCacheSupportedTypes`` / hardware
    ``displayMode``) is set via the transform's ``overrideDisplayType``
    attribute.  When *enabled* is True the object uses a bounding-box (2)
    display type to hint the GPU path; set False to restore normal (0).

    Note: This is a lightweight approximation for environments without a
    full GPU cache plug-in.  It exposes the ``overrideEnabled`` /
    ``overrideDisplayType`` attributes that are available on every Maya node.

    Args:
        object_name: Transform or shape node name.
        enabled: True to enable GPU override display (bounding box mode),
            False to restore normal display.  Default: True.

    Returns:
        ToolResult dict with ``context.object_name``,
        ``context.enabled``, ``context.display_type``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        if enabled:
            # 2 = bounding box display type
            cmds.setAttr("{}.overrideEnabled".format(object_name), True)
            cmds.setAttr("{}.overrideDisplayType".format(object_name), 2)
            display_type = 2
        else:
            cmds.setAttr("{}.overrideEnabled".format(object_name), False)
            cmds.setAttr("{}.overrideDisplayType".format(object_name), 0)
            display_type = 0

        return skill_success(
            "{} GPU override on '{}'".format("Enabled" if enabled else "Disabled", object_name),
            object_name=object_name,
            enabled=enabled,
            display_type=display_type,
            prompt="Check the result with list_scene_utils or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to toggle GPU override on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`toggle_gpu_override`."""
    return toggle_gpu_override(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
