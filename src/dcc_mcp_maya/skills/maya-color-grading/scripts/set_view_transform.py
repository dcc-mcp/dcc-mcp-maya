"""Set the viewport color transform (view LUT)."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        enabled = cmds.colorManagementPrefs(query=True, cmEnabled=True)
        if not enabled:
            cmds.colorManagementPrefs(edit=True, cmEnabled=True)

        cmds.colorManagementPrefs(edit=True, viewTransformName=view_transform)

        applied = cmds.colorManagementPrefs(query=True, viewTransformName=True) or ""

        return skill_success(
            "Set view transform to '{}'".format(applied),
            prompt="Use get_color_management_info to verify all color settings.",
            view_transform=applied,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set view transform")


@skill_entry
def main(**kwargs):
    return set_view_transform(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
