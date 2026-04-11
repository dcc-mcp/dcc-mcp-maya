"""List all available color spaces registered in Maya's color management."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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

        return maya_success(
            "Color space list retrieved",
            color_management_enabled=cm_enabled,
            input_color_spaces=list(spaces),
            rendering_spaces=list(rendering_spaces),
            output_transforms=list(output_transforms),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to list color spaces")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_color_spaces`."""
    return list_color_spaces(**kwargs)

if __name__ == "__main__":
    import json

    result = list_color_spaces()
    print(json.dumps(result))
