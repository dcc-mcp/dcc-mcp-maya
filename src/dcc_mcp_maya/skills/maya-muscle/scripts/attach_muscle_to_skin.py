"""Attach a Maya Muscle capsule to a cMuscleSystem skin deformer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def attach_muscle_to_skin(muscle_node: str, skin_deformer: str) -> dict:
    """Attach a cMuscleObject capsule to a cMuscleSystem skin deformer.

    Args:
        muscle_node: Name of the cMuscleObject shape or transform.
        skin_deformer: Name of the cMuscleSystem deformer node.

    Returns:
        ActionResultModel dict confirming the attachment.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not muscle_node or not skin_deformer:
        return error_result(
            "muscle_node and skin_deformer are required",
            "Provide both the muscle and the cMuscleSystem deformer names.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for node in (muscle_node, skin_deformer):
            if not cmds.objExists(node):
                return error_result(
                    "Node '{}' does not exist".format(node),
                    "Verify the node names with list_muscles.",
                ).to_dict()

        deformer_type = cmds.objectType(skin_deformer)
        if deformer_type != "cMuscleSystem":
            return error_result(
                "Node '{}' is not a cMuscleSystem deformer (got '{}')".format(skin_deformer, deformer_type),
                "Provide a valid cMuscleSystem deformer name.",
            ).to_dict()

        cmds.cMuscleSystem(skin_deformer, edit=True, addMuscle=muscle_node)

        return success_result(
            "Attached muscle '{}' to skin deformer '{}'".format(muscle_node, skin_deformer),
            prompt=(
                "Muscle attached. Paint muscle weights with the cMuscle weight tool, "
                "or set_muscle_attribute to tune squash/stretch."
            ),
            muscle_node=muscle_node,
            skin_deformer=skin_deformer,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("attach_muscle_to_skin failed")
        return error_result("Failed to attach muscle to skin", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return attach_muscle_to_skin(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(attach_muscle_to_skin("cMuscleObject1", "cMuscleSystem1")))
