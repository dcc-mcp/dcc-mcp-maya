"""Build a simple radial joint hierarchy over a set of objects (issue #306).

Stage three: create a centre root joint plus one child joint snapped to each
object's world position, giving later stages a skeleton to bind and animate.
"""

from __future__ import annotations

from typing import List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def create_rig_joints(
    objects: List[str],
    center_position: List[float] = None,
    joint_prefix: str = "procJnt",
    root_name: str = "procRoot",
) -> dict:
    """Create a root joint and a child joint at each object's position.

    Args:
        objects: Transform names whose positions seed the child joints.
        center_position: World position ``[x, y, z]`` for the root joint.
        joint_prefix: Prefix for child joint names.
        root_name: Name for the root joint.

    Returns:
        ToolResult dict with ``context.root_joint`` and ``context.joints``.
    """
    if not objects:
        return maya_error("No objects", "objects must contain at least one name")
    if center_position is None:
        center_position = [0.0, 0.0, 0.0]
    if len(center_position) != 3:
        return maya_error("Invalid center_position", "center_position must be [x, y, z]")

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

        cmds.select(clear=True)
        root = cmds.joint(name=root_name, position=center_position)
        joints: List[str] = []
        for i, obj in enumerate(objects):
            pos = cmds.xform(obj, query=True, worldSpace=True, translation=True)
            cmds.select(root, replace=True)
            jnt = cmds.joint(name="{}{}".format(joint_prefix, i + 1), position=pos)
            joints.append(jnt)

        return maya_success(
            "Created root joint {} with {} child joints".format(root, len(joints)),
            prompt="Use bind_objects_to_joints to attach the objects to these joints.",
            root_joint=root,
            joints=joints,
            count=len(joints),
        )
    except Exception as exc:  # noqa: BLE001
        return maya_from_exception(exc, message="Failed to create rig joints")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_rig_joints`."""
    return create_rig_joints(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
