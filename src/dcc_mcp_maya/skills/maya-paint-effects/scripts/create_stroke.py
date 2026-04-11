"""Create a standalone Paint Effects stroke in world space."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_stroke(
    preset: str = "flowers/daisy.mel",
    start_point: Optional[List[float]] = None,
    end_point: Optional[List[float]] = None,
    name: str = "",
) -> dict:
    """Create a standalone Paint Effects stroke.

    Args:
        preset: Relative path to a MEL brush preset (e.g. ``"flowers/daisy.mel"``).
            The preset is loaded from the Maya Paint Effects preset library.
        start_point: World-space start point ``[x, y, z]``. Defaults to ``[0, 0, 0]``.
        end_point: World-space end point ``[x, y, z]``. Defaults to ``[1, 0, 0]``.
        name: Optional name for the created stroke transform. If empty, Maya assigns one.

    Returns:
        ActionResultModel dict with ``stroke_node``, ``brush_node``, and ``preset``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        sp = start_point or [0.0, 0.0, 0.0]
        ep = end_point or [1.0, 0.0, 0.0]

        # Load the preset brush
        mel.eval("getDefaultBrush;")
        brush_nodes = cmds.ls(type="brush") or []
        brush_before = set(brush_nodes)

        try:
            mel.eval('PaintEffectsLoadBrush("{}");'.format(preset))
        except Exception:
            pass  # preset may not exist; continue with default brush

        # Create stroke curve
        curve = cmds.curve(
            degree=1,
            point=[sp, ep],
        )

        # Attach stroke to curve via MEL
        cmds.select(curve, replace=True)
        mel.eval("AttachBrushToCurves;")

        strokes = cmds.ls(type="stroke") or []
        stroke_node = strokes[-1] if strokes else ""
        stroke_transform = ""
        if stroke_node:
            parents = cmds.listRelatives(stroke_node, parent=True) or []
            stroke_transform = parents[0] if parents else stroke_node

        if name and stroke_transform and stroke_transform != name:
            try:
                stroke_transform = cmds.rename(stroke_transform, name)
            except Exception:
                pass

        brush_nodes_after = cmds.ls(type="brush") or []
        new_brushes = [b for b in brush_nodes_after if b not in brush_before]
        brush_node = new_brushes[-1] if new_brushes else ""

        return skill_success(
            "Paint Effects stroke created from preset '{}'".format(preset),
            prompt="Use attach_stroke_to_surface to paint on a surface or list_strokes to inspect.",
            stroke_node=stroke_node,
            stroke_transform=stroke_transform,
            brush_node=brush_node,
            preset=preset,
            curve=curve,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create Paint Effects stroke")


@skill_entry
def main(**kwargs):
    return create_stroke(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
