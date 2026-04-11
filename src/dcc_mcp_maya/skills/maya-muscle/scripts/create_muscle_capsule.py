"""Create a Maya Muscle capsule (cMuscleObject) between two joints."""

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
    """Create a cMuscleObject capsule muscle between two joints.

    Args:
        start_joint: Start joint name.
        end_joint: End joint name.
        name: Optional name for the muscle node transform.
        radius: Capsule radius. Default ``1.0``.

    Returns:
        ActionResultModel dict with ``context.muscle_node`` and ``context.radius``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        for jnt in (start_joint, end_joint):
            if not cmds.objExists(jnt):
                return error_result(
                    "Joint '{}' not found".format(jnt),
                    "Verify joint names using the Outliner.",
                ).to_dict()

        cmds.loadPlugin("MayaMuscle", quiet=True)
        cmds.select([start_joint, end_joint], replace=True)
        mel.eval("cMuscle_makeMuscle(0)")

        muscle_nodes = cmds.ls(type="cMuscleObject") or []
        muscle_node = muscle_nodes[-1] if muscle_nodes else ""

        if muscle_node and name:
            parent = cmds.listRelatives(muscle_node, parent=True) or []
            if parent:
                cmds.rename(parent[0], name)
            muscle_node = cmds.ls(type="cMuscleObject")[-1]

        if muscle_node:
            cmds.setAttr("{}.radius0".format(muscle_node), radius)
            cmds.setAttr("{}.radius1".format(muscle_node), radius)

        return success_result(
            "Muscle capsule created: '{}'".format(muscle_node),
            prompt="Muscle created. Use apply_muscle_skin to connect it to a mesh.",
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


def main(**kwargs):
    return create_muscle_capsule(**kwargs)


if __name__ == "__main__":
    import json

    result = create_muscle_capsule("shoulder_jnt", "elbow_jnt")
    print(json.dumps(result))
