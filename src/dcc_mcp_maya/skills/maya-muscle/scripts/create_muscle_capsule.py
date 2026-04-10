"""Create a Maya Muscle cMuscleObject capsule between two joints."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_muscle_capsule(
    start_joint: str,
    end_joint: str,
    name: Optional[str] = None,
    radius: float = 1.0,
) -> dict:
    """Create a cMuscleObject capsule driven by two joints.

    Args:
        start_joint: Name of the start (root) joint.
        end_joint: Name of the end (tip) joint.
        name: Optional name for the muscle capsule node.
        radius: Capsule cross-section radius.

    Returns:
        ActionResultModel dict with ``context.muscle_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not start_joint or not end_joint:
        return error_result(
            "start_joint and end_joint are required",
            "Provide valid joint names.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for jnt in (start_joint, end_joint):
            if not cmds.objExists(jnt):
                return error_result(
                    "Joint '{}' does not exist".format(jnt),
                    "Check the joint name and try again.",
                ).to_dict()

        # Load cMuscle plugin
        if not cmds.pluginInfo("cMuscle", query=True, loaded=True):
            cmds.loadPlugin("cMuscle", quiet=True)

        create_kwargs = {
            "startJoint": start_joint,
            "endJoint": end_joint,
            "radius": radius,
        }
        if name:
            create_kwargs["name"] = name

        muscle_node = cmds.cMuscleObject(**create_kwargs)

        return success_result(
            "Created muscle capsule '{}' between '{}' and '{}'".format(muscle_node, start_joint, end_joint),
            prompt=(
                "Muscle capsule created. Use attach_muscle_to_skin to bind it to a skin deformer, "
                "or set_muscle_attribute to tune rest/squash/stretch values."
            ),
            muscle_node=muscle_node,
            start_joint=start_joint,
            end_joint=end_joint,
            radius=radius,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_muscle_capsule failed")
        return error_result("Failed to create muscle capsule", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_muscle_capsule(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_muscle_capsule("joint1", "joint2")))
