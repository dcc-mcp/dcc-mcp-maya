"""Create a Maya joint node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if parent and not cmds.objExists(parent):
            return error_result(
                "Parent not found: {}".format(parent),
                "'{}' does not exist in the scene".format(parent),
            ).to_dict()

        pos = position or [0.0, 0.0, 0.0]
        if len(pos) != 3:
            return error_result(
                "Invalid position",
                "position must be a list of 3 floats, got: {}".format(pos),
            ).to_dict()

        # Select parent first so joint is created as its child
        if parent:
            cmds.select(parent, replace=True)
        else:
            cmds.select(clear=True)

        kwargs = {"position": (pos[0], pos[1], pos[2])}
        if name:
            kwargs["name"] = name

        joint_name = cmds.joint(**kwargs)

        return success_result(
            "Created joint '{}'".format(joint_name),
            object_name=joint_name,
            position=pos,
            parent=parent,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_joint failed")
        return error_result("Failed to create joint", str(exc)).to_dict()


def main(**kwargs):
    return create_joint(**kwargs)


if __name__ == "__main__":
    import json

    result = create_joint()
    print(json.dumps(result))
