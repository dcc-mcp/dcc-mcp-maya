"""Create a procedural distribution of polygon spheres (issue #306).

Typed, schema-validated alternative to a hand-rolled ``execute_python`` loop
for the first stage of a procedural rig/animation workflow: place ``count``
spheres in a deterministic spherical / grid / line layout and return the
created object names so later stages (materials, joints, animation) can
consume them.
"""

from __future__ import annotations

import math
from typing import List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_LAYOUTS = ("sphere", "grid", "line")


def _sphere_positions(count: int, radius: float) -> List[List[float]]:
    """Even points on a sphere via the Fibonacci lattice (deterministic)."""
    if count == 1:
        return [[0.0, 0.0, 0.0]]
    points: List[List[float]] = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(count):
        y = 1.0 - (i / float(count - 1)) * 2.0
        r = math.sqrt(max(0.0, 1.0 - y * y))
        theta = golden * i
        points.append([math.cos(theta) * r * radius, y * radius, math.sin(theta) * r * radius])
    return points


def _grid_positions(count: int, spacing: float) -> List[List[float]]:
    side = int(math.ceil(math.sqrt(count)))
    offset = (side - 1) * spacing / 2.0
    out: List[List[float]] = []
    for i in range(count):
        row, col = divmod(i, side)
        out.append([col * spacing - offset, 0.0, row * spacing - offset])
    return out


def _line_positions(count: int, spacing: float) -> List[List[float]]:
    offset = (count - 1) * spacing / 2.0
    return [[i * spacing - offset, 0.0, 0.0] for i in range(count)]


def create_sphere_layout(
    count: int = 8,
    radius: float = 1.0,
    layout: str = "sphere",
    spacing: float = 4.0,
    distribution_radius: float = 10.0,
    name_prefix: str = "procSphere",
) -> dict:
    """Create ``count`` polygon spheres in a procedural layout.

    Args:
        count: Number of spheres to create (1-500).
        radius: Per-sphere radius.
        layout: ``sphere`` (Fibonacci shell), ``grid`` (XZ grid), or ``line``.
        spacing: Distance between spheres for ``grid`` / ``line`` layouts.
        distribution_radius: Shell radius for the ``sphere`` layout.
        name_prefix: Prefix for created transform names.

    Returns:
        ToolResult dict with ``context.object_names`` and ``context.count``.
    """
    if layout not in _LAYOUTS:
        return maya_error(
            "Invalid layout",
            "layout must be one of {}".format(", ".join(_LAYOUTS)),
        )
    count = int(count)
    if count < 1 or count > 500:
        return maya_error("Invalid count", "count must be between 1 and 500")

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )

    try:
        if layout == "sphere":
            positions = _sphere_positions(count, distribution_radius)
        elif layout == "grid":
            positions = _grid_positions(count, spacing)
        else:
            positions = _line_positions(count, spacing)

        object_names: List[str] = []
        for i, pos in enumerate(positions):
            transform = cmds.polySphere(radius=radius, name="{}{}".format(name_prefix, i + 1))[0]
            cmds.move(pos[0], pos[1], pos[2], transform, absolute=True)
            object_names.append(transform)

        return maya_success(
            "Created {} spheres in a {} layout".format(len(object_names), layout),
            prompt="Pass object_names to assign_palette_materials or create_rig_joints next.",
            object_names=object_names,
            count=len(object_names),
            layout=layout,
        )
    except Exception as exc:  # noqa: BLE001
        return maya_from_exception(exc, message="Failed to create sphere layout")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_sphere_layout`."""
    return create_sphere_layout(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
