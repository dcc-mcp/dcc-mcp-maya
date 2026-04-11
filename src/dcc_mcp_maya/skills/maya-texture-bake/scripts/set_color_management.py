"""Configure scene color management (OCIO / Maya native)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

logger = logging.getLogger(__name__)


def set_color_management(
    enabled: bool = True,
    input_color_space: Optional[str] = None,
    rendering_space: Optional[str] = None,
    output_transform: Optional[str] = None,
) -> dict:
    """Configure scene color management (OCIO / Maya native).

    Args:
        enabled: Enable or disable color management globally.  Default: True.
        input_color_space: Input color space name (e.g. ``"sRGB"``,
            ``"ACEScg"``).  If None, leaves the current setting unchanged.
        rendering_space: Rendering/working color space (e.g. ``"scene-linear
            Rec 709/sRGB"``).  If None, leaves unchanged.
        output_transform: Output view transform name (e.g.
            ``"sRGB gamma"``).  If None, leaves unchanged.

    Returns:
        ActionResultModel dict with current color management configuration.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Toggle color management
        cmds.colorManagementPrefs(edit=True, cmEnabled=enabled)

        if input_color_space:
            try:
                cmds.colorManagementPrefs(edit=True, inputColorSpace=input_color_space)
            except Exception as exc:
                logger.warning("Could not set inputColorSpace '%s': %s", input_color_space, exc)

        if rendering_space:
            try:
                cmds.colorManagementPrefs(edit=True, renderingSpaceName=rendering_space)
            except Exception as exc:
                logger.warning("Could not set renderingSpace '%s': %s", rendering_space, exc)

        if output_transform:
            try:
                cmds.colorManagementPrefs(edit=True, outputTransformName=output_transform)
            except Exception as exc:
                logger.warning("Could not set outputTransform '%s': %s", output_transform, exc)

        # Query resulting state
        try:
            cm_enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        except Exception:
            cm_enabled = enabled

        try:
            current_rendering = cmds.colorManagementPrefs(query=True, renderingSpaceName=True)
        except Exception:
            current_rendering = rendering_space

        try:
            current_output = cmds.colorManagementPrefs(query=True, outputTransformName=True)
        except Exception:
            current_output = output_transform

        return maya_success(
            "Color management {}".format("enabled" if enabled else "disabled"),
            enabled=cm_enabled,
            rendering_space=current_rendering,
            output_transform=current_output,
            input_color_space=input_color_space,
            prompt="Check the result with list_texture_bake or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set color management")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_color_management`."""
    return set_color_management(**kwargs)


if __name__ == "__main__":
    import json

    result = set_color_management()
    print(json.dumps(result))
