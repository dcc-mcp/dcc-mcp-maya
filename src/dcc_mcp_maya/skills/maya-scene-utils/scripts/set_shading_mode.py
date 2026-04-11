"""Set the viewport shading mode for the active or specified panel."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional

def set_shading_mode(
    mode: str = "smooth",
    panel: Optional[str] = None,
) -> dict:
    """Set the viewport shading mode for the active or specified panel.

    Changes how geometry is displayed in Maya's model view panels.

    Available modes:
    - ``"wireframe"`` — wireframe only (no shading)
    - ``"smooth"`` — smooth shaded (default, no textures)
    - ``"textured"`` — smooth shaded with texture display
    - ``"flat"`` — flat shaded polygons
    - ``"bounding_box"`` — bounding box only (fastest)

    Args:
        mode: Target display mode.  Default: ``"smooth"``.
        panel: Name of the model panel to affect (e.g. ``"modelPanel1"``).
            If None, uses the first model panel found via ``cmds.getPanel``.

    Returns:
        ActionResultModel dict with ``context.mode``, ``context.panel``.
    """

    _MODE_MAP = {
        "wireframe": ("wireframeOnShaded", False),
        "smooth": ("smoothShaded", False),
        "textured": ("textured", True),
        "flat": ("flatShaded", False),
        "bounding_box": ("boundingBox", False),
    }

    mode_lower = mode.lower()
    if mode_lower not in _MODE_MAP:
        return maya_error(
            "Invalid mode: {}".format(mode),
            "mode must be one of {}".format(sorted(_MODE_MAP.keys())),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Resolve target panel
        if panel:
            if not cmds.modelPanel(panel, query=True, exists=True):
                return maya_error(
                    "Panel not found: {}".format(panel),
                    "'{}' is not a valid model panel".format(panel),
                )
            target_panel = panel
        else:
            panels = cmds.getPanel(type="modelPanel") or []
            if not panels:
                return maya_error(
                    "No model panels found",
                    "Could not locate any Maya model view panel",
                )
            target_panel = panels[0]

        # Apply the shading mode
        if mode_lower == "wireframe":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="wireframe", displayTextures=False)
        elif mode_lower == "smooth":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="smoothShaded", displayTextures=False)
        elif mode_lower == "textured":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="smoothShaded", displayTextures=True)
        elif mode_lower == "flat":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="flatShaded", displayTextures=False)
        elif mode_lower == "bounding_box":
            cmds.modelEditor(target_panel, edit=True, displayAppearance="boundingBox", displayTextures=False)

        return maya_success(
            "Set shading mode to '{}' on panel '{}'".format(mode_lower, target_panel),
            mode=mode_lower,
            panel=target_panel,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to set shading mode")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_shading_mode`."""
    return set_shading_mode(**kwargs)

if __name__ == "__main__":
    import json

    result = set_shading_mode()
    print(json.dumps(result))
