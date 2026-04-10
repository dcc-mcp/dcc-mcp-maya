"""Set the scene's rendering color space."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_rendering_space(rendering_space: str) -> dict:
    """Set the rendering color space for the current Maya scene.

    Common values depend on the configured color management:
    - ``"ACEScg"`` — ACES CG linear space (standard VFX pipeline)
    - ``"scene-linear Rec 709/sRGB"`` — Maya default linear space
    - ``"sRGB"`` — sRGB display space
    - Any valid color space name from the active OCIO config.

    Args:
        rendering_space: Name of the rendering color space to activate.

    Returns:
        ActionResultModel dict with ``context.rendering_space``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        if not enabled:
            cmds.colorManagementPrefs(edit=True, cmEnabled=True)

        cmds.colorManagementPrefs(edit=True, renderingSpaceName=rendering_space)

        applied = cmds.colorManagementPrefs(query=True, renderingSpaceName=True) or ""

        return success_result(
            "Set rendering space to '{}'".format(applied),
            prompt="Use get_color_management_info to verify all color settings.",
            rendering_space=applied,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_rendering_space failed")
        return error_result("Failed to set rendering space", str(exc)).to_dict()


def main(**kwargs):
    return set_rendering_space(**kwargs)


if __name__ == "__main__":
    import json

    result = set_rendering_space("ACEScg")
    print(json.dumps(result))
