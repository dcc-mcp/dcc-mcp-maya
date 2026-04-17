"""Attach a Paint Effects brush preset to a NURBS or polygon surface."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def attach_stroke_to_surface(
    surface: str,
    preset: str = "flowers/daisy.mel",
    stroke_count: int = 10,
    name: str = "",
) -> dict:
    """Attach a Paint Effects brush preset to a surface.

    Args:
        surface: Name of the NURBS or polygon surface (transform or shape).
        preset: Relative path to a brush preset, e.g. ``"grasses/grass.mel"``.
        stroke_count: Number of strokes to scatter on the surface.  Default: 10.
        name: Optional name prefix for the created stroke nodes.

    Returns:
        ToolResult dict with ``surface``, ``preset``, ``strokes_created``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        err = validate_node_exists(cmds, surface)
        if err:
            return err

        strokes_before = set(cmds.ls(type="stroke") or [])

        # Load preset and select surface
        try:
            mel.eval('PaintEffectsLoadBrush("{}");'.format(preset))
        except Exception:
            pass

        cmds.select(surface, replace=True)
        # Use makePaintable MEL to scatter on surface
        for _ in range(stroke_count):
            mel.eval("AttachBrushToCurves;")

        strokes_after = cmds.ls(type="stroke") or []
        new_strokes = [s for s in strokes_after if s not in strokes_before]

        if name:
            renamed = []
            for i, s in enumerate(new_strokes):
                parents = cmds.listRelatives(s, parent=True) or []
                t = parents[0] if parents else s
                try:
                    t = cmds.rename(t, "{}_{}".format(name, i))
                except Exception:
                    pass
                renamed.append(t)
        else:
            renamed = new_strokes

        return skill_success(
            "Attached {} stroke(s) to surface '{}'".format(len(new_strokes), surface),
            prompt="Use list_strokes to inspect or delete_stroke to remove unwanted strokes.",
            surface=surface,
            preset=preset,
            strokes_created=len(new_strokes),
            stroke_nodes=renamed,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to attach stroke to surface")


@skill_entry
def main(**kwargs):
    return attach_stroke_to_surface(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
