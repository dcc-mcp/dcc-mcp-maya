"""Delete a Maya Muscle cMuscleObject capsule."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_muscle(muscle_node: str) -> dict:
    """Delete a Maya Muscle capsule (cMuscleObject) and its transform.

    Args:
        muscle_node: Name of the cMuscleObject shape or its parent transform.

    Returns:
        ActionResultModel dict confirming deletion.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not muscle_node:
        return error_result("No muscle node specified", "Provide the cMuscleObject name.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(muscle_node):
            return error_result(
                "Muscle node '{}' does not exist".format(muscle_node),
                "Check the node name with list_muscles.",
            ).to_dict()

        node_type = cmds.objectType(muscle_node)
        if node_type == "cMuscleObject":
            parents = cmds.listRelatives(muscle_node, parent=True, fullPath=False) or []
            target = parents[0] if parents else muscle_node
        else:
            target = muscle_node

        cmds.delete(target)

        return success_result(
            "Deleted muscle capsule '{}'".format(muscle_node),
            prompt="Muscle deleted. Use create_muscle_capsule to add a new one.",
            deleted_node=muscle_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_muscle failed")
        return error_result("Failed to delete muscle", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return delete_muscle(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(delete_muscle("cMuscleObject1")))
