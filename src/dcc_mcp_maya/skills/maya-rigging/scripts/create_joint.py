"""Create a Maya joint node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def create_joint(
    name: Optional[str] = None,
    position: Optional[List[float]] = None,
    parent: Optional[str] = None,
) -> dict:
    """Create a Maya joint node.

    Joints are the fundamental building blocks for skeletal rigs used in
    character animation.  If a *parent* is specified the joint is created as
    a child of that node; otherwise it is placed at the world root.

    Args:
        name: Optional name for the new joint.  Maya generates a default name
            (``"joint1"``, ``"joint2"``, …) when None.
        position: World-space ``[x, y, z]`` position.  Defaults to
            ``[0, 0, 0]``.
        parent: Name of an existing transform/joint to parent the new joint
            under.  If None, the joint is created at the world root.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.position``, and ``context.parent``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if parent:
            err = validate_node_exists(cmds, parent)
            if err:
                return err

        pos = position or [0.0, 0.0, 0.0]
        if len(pos) != 3:
            return skill_error(
                "Invalid position",
                "position must be a list of 3 floats, got: {}".format(pos),
            )

        # Select parent first so joint is created as its child
        if parent:
            cmds.select(parent, replace=True)
        else:
            cmds.select(clear=True)

        kwargs = {"position": (pos[0], pos[1], pos[2])}
        if name:
            kwargs["name"] = name

        joint_name = cmds.joint(**kwargs)

        return skill_success(
            "Created joint '{}'".format(joint_name),
            object_name=joint_name,
            position=pos,
            parent=parent,
            prompt="Use bind_skin or add_ik_handle to complete the rig.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create joint")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_joint`."""
    return create_joint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
