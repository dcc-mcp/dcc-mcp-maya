"""List all available color spaces registered in Maya's color management."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


def list_color_spaces() -> dict:
    """List all available color spaces registered in Maya's color management.

    Returns:
        ActionResultModel dict with ``context.color_spaces`` list.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        try:
            spaces = cmds.colorManagementPrefs(query=True, inputColorSpaceNames=True) or []
        except Exception:
            spaces = []

        try:
            rendering_spaces = cmds.colorManagementPrefs(query=True, renderingSpaceNames=True) or []
        except Exception:
            rendering_spaces = []

        try:
            output_transforms = cmds.colorManagementPrefs(query=True, outputTransformNames=True) or []
        except Exception:
            output_transforms = []

        try:
            cm_enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        except Exception:
            cm_enabled = False

        return skill_success(
            "Color space list retrieved",
            color_management_enabled=cm_enabled,
            input_color_spaces=list(spaces),
            rendering_spaces=list(rendering_spaces),
            output_transforms=list(output_transforms),
            prompt="Check the result with list_texture_bake or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list color spaces")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_color_spaces`."""
    return list_color_spaces(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
