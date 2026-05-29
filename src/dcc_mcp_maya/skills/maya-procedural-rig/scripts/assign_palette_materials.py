"""Assign a generated colour palette across a set of objects (issue #306).

Stage two of the procedural workflow: shade the objects produced by
``create_sphere_layout`` with deterministic per-object Lambert materials so the
playblast at the end of the chain is visually legible.
"""

from __future__ import annotations

import colorsys
import random
from typing import List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_PALETTES = ("rainbow", "random", "mono")


def _palette_colors(palette: str, count: int, seed: int, base_hue: float) -> List[List[float]]:
    rng = random.Random(seed)
    colors: List[List[float]] = []
    for i in range(count):
        if palette == "rainbow":
            hue = (i / float(max(1, count))) % 1.0
            colors.append(list(colorsys.hsv_to_rgb(hue, 0.85, 0.95)))
        elif palette == "mono":
            value = 0.35 + 0.6 * (i / float(max(1, count - 1))) if count > 1 else 0.8
            colors.append(list(colorsys.hsv_to_rgb(base_hue, 0.7, value)))
        else:  # random
            colors.append(list(colorsys.hsv_to_rgb(rng.random(), 0.8, 0.9)))
    return colors


def assign_palette_materials(
    objects: List[str],
    palette: str = "rainbow",
    seed: int = 0,
    base_hue: float = 0.58,
    material_prefix: str = "procMat",
) -> dict:
    """Create and assign one Lambert material per object from a palette.

    Args:
        objects: Transform names to shade (typically from create_sphere_layout).
        palette: ``rainbow``, ``random``, or ``mono``.
        seed: Seed for the ``random`` palette (deterministic).
        base_hue: Hue (0-1) used as the anchor for the ``mono`` palette.
        material_prefix: Prefix for created shading-node names.

    Returns:
        ToolResult dict with ``context.assignments`` and ``context.material_count``.
    """
    if palette not in _PALETTES:
        return maya_error(
            "Invalid palette",
            "palette must be one of {}".format(", ".join(_PALETTES)),
        )
    if not objects:
        return maya_error("No objects", "objects must contain at least one name")

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )

    try:
        missing = [obj for obj in objects if not cmds.objExists(obj)]
        if missing:
            return maya_error(
                "Objects not found",
                "missing: {}".format(", ".join(missing)),
                possible_solutions=["Run create_sphere_layout first and reuse object_names"],
            )

        colors = _palette_colors(palette, len(objects), seed, base_hue)
        assignments = []
        for i, obj in enumerate(objects):
            shader = cmds.shadingNode("lambert", asShader=True, name="{}{}".format(material_prefix, i + 1))
            sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{}SG".format(shader))
            cmds.connectAttr("{}.outColor".format(shader), "{}.surfaceShader".format(sg), force=True)
            r, g, b = colors[i]
            cmds.setAttr("{}.color".format(shader), r, g, b, type="double3")
            cmds.sets(obj, edit=True, forceElement=sg)
            assignments.append({"object": obj, "material": shader, "color": [round(r, 3), round(g, 3), round(b, 3)]})

        return maya_success(
            "Assigned {} materials using the {} palette".format(len(assignments), palette),
            prompt="Continue with create_rig_joints to build a skeleton over these objects.",
            assignments=assignments,
            material_count=len(assignments),
            palette=palette,
        )
    except Exception as exc:  # noqa: BLE001
        return maya_from_exception(exc, message="Failed to assign palette materials")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_palette_materials`."""
    return assign_palette_materials(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
