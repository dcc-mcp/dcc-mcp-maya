"""Bind objects to joints in parallel order (issue #306).

Stage four: attach each object to its matching joint so animating the joints
drives the geometry. Supports constraint-based or parent-based binding.
"""

from __future__ import annotations

from typing import List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_BIND_MODES = ("parentConstraint", "parent", "point")


def bind_objects_to_joints(
    objects: List[str],
    joints: List[str],
    bind_mode: str = "parentConstraint",
    maintain_offset: bool = True,
) -> dict:
    """Bind ``objects[i]`` to ``joints[i]`` using the chosen mode.

    Args:
        objects: Transform names to bind (parallel to ``joints``).
        joints: Joint names driving each object (parallel to ``objects``).
        bind_mode: ``parentConstraint``, ``point``, or ``parent`` (re-parent).
        maintain_offset: Keep the current relative offset for constraints.

    Returns:
        ToolResult dict with ``context.bindings`` and ``context.bound_count``.
    """
    if bind_mode not in _BIND_MODES:
        return maya_error(
            "Invalid bind_mode",
            "bind_mode must be one of {}".format(", ".join(_BIND_MODES)),
        )
    if not objects or not joints:
        return maya_error("Missing input", "objects and joints must both be non-empty")
    if len(objects) != len(joints):
        return maya_error(
            "Length mismatch",
            "objects ({}) and joints ({}) must be the same length".format(len(objects), len(joints)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return maya_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )

    try:
        bindings = []
        for obj, jnt in zip(objects, joints):
            if not cmds.objExists(obj) or not cmds.objExists(jnt):
                return maya_error(
                    "Node not found",
                    "missing object or joint: {} / {}".format(obj, jnt),
                )
            if bind_mode == "parent":
                cmds.parent(obj, jnt)
                node = obj
            elif bind_mode == "point":
                node = cmds.pointConstraint(jnt, obj, maintainOffset=maintain_offset)[0]
            else:
                node = cmds.parentConstraint(jnt, obj, maintainOffset=maintain_offset)[0]
            bindings.append({"object": obj, "joint": jnt, "binding": node})

        return maya_success(
            "Bound {} objects using {}".format(len(bindings), bind_mode),
            prompt="Use keyframe_orbit_animation to animate the joints.",
            bindings=bindings,
            bound_count=len(bindings),
            bind_mode=bind_mode,
        )
    except Exception as exc:  # noqa: BLE001
        return maya_from_exception(exc, message="Failed to bind objects to joints")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`bind_objects_to_joints`."""
    return bind_objects_to_joints(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
