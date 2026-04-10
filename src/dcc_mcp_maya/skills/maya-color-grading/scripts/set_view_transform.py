"""Set the viewport color transform (view LUT)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_view_transform(view_transform: str) -> dict:
    """Set the viewport color transform (view LUT) for Maya.

    The view transform controls how rendered colors are displayed in the
    viewport and render viewer.  Common values:

    - ``"Un-tone-mapped"`` / ``"Raw"`` — No LUT (linear pass-through)
    - ``"sRGB gamma"`` — sRGB display transform
    - ``"ACES 1.0 SDR-video"`` — ACES output transform for SDR monitors

    Args:
        view_transform: Name of the view transform to apply.

    Returns:
        ActionResultModel dict with ``context.view_transform``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        if not enabled:
            cmds.colorManagementPrefs(edit=True, cmEnabled=True)

        cmds.colorManagementPrefs(edit=True, viewTransformName=view_transform)

        applied = cmds.colorManagementPrefs(query=True, viewTransformName=True) or ""

        return success_result(
            "Set view transform to '{}'".format(applied),
            prompt="Use get_color_management_info to verify all color settings.",
            view_transform=applied,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_view_transform failed")
        return error_result("Failed to set view transform", str(exc)).to_dict()


def main(**kwargs):
    return set_view_transform(**kwargs)


if __name__ == "__main__":
    import json

    result = set_view_transform("sRGB gamma")
    print(json.dumps(result))
