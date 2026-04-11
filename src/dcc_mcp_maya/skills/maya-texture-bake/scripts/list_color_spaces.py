"""List all available color spaces registered in Maya's color management."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_color_spaces() -> dict:
    """List all available color spaces registered in Maya's color management.

    Returns:
        ActionResultModel dict with ``context.color_spaces`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

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

        return success_result(
            "Color space list retrieved",
            color_management_enabled=cm_enabled,
            input_color_spaces=list(spaces),
            rendering_spaces=list(rendering_spaces),
            output_transforms=list(output_transforms),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_color_spaces failed")
        return error_result("Failed to list color spaces", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_color_spaces`."""
    return list_color_spaces(**kwargs)


if __name__ == "__main__":
    import json

    result = list_color_spaces()
    print(json.dumps(result))
