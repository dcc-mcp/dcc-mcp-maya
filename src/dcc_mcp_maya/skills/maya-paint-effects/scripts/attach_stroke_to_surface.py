"""Attach a Paint Effects brush preset to a NURBS or polygon surface."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
        ActionResultModel dict with ``surface``, ``preset``, ``strokes_created``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        if not cmds.objExists(surface):
            return error_result(
                "Surface not found: {}".format(surface),
                "Ensure the surface exists before attaching strokes",
            ).to_dict()

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

        return success_result(
            "Attached {} stroke(s) to surface '{}'".format(len(new_strokes), surface),
            prompt="Use list_strokes to inspect or delete_stroke to remove unwanted strokes.",
            surface=surface,
            preset=preset,
            strokes_created=len(new_strokes),
            stroke_nodes=renamed,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("attach_stroke_to_surface failed")
        return error_result("Failed to attach stroke to surface", str(exc)).to_dict()


def main(**kwargs):
    return attach_stroke_to_surface(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(attach_stroke_to_surface("pSphere1")))
