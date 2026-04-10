"""Retarget motion capture data from a source character to a target character."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Retarget mocap animation from source character to target character.

    Args:
        params: Dictionary with keys:
            - source_character (str): HIKCharacterNode used as motion source.
            - target_character (str): HIKCharacterNode to receive retargeted motion.
            - start_frame (float): Start frame for baking. Default current start.
            - end_frame (float): End frame for baking. Default current end.
            - bake (bool): If True, bake the retargeted animation to keyframes. Default True.

    Returns:
        ActionResultModel with retargeting result.
    """
    source = params.get("source_character", "")
    target = params.get("target_character", "")
    bake = params.get("bake", True)
    start_frame = params.get("start_frame", None)
    end_frame = params.get("end_frame", None)

    if not source:
        return error_result("Invalid parameter", "source_character must not be empty.")
    if not target:
        return error_result("Invalid parameter", "target_character must not be empty.")

    try:
        # Validate nodes exist and are HIKCharacterNode
        for node, label in [(source, "source_character"), (target, "target_character")]:
            if not cmds.objExists(node):
                return error_result(
                    "Node not found: '{0}'".format(node),
                    "{0} does not exist in the scene.".format(label),
                )
            if cmds.nodeType(node) != "HIKCharacterNode":
                return error_result(
                    "Invalid node type for '{0}'".format(node),
                    "Expected HIKCharacterNode, got {0}.".format(cmds.nodeType(node)),
                )

        # Connect source motion to target via HIKRetargeter
        retargeter = cmds.createNode("HIKRetargeter", name="{0}_retargeter".format(target))
        cmds.connectAttr(
            "{0}.OutputCharacterDefinition".format(source),
            "{0}.InputCharacterizationSrc".format(retargeter),
        )
        cmds.connectAttr(
            "{0}.OutputCharacterDefinition".format(target),
            "{0}.InputCharacterizationDst".format(retargeter),
        )

        if bake:
            time_range = cmds.playbackOptions(query=True, minTime=True), cmds.playbackOptions(query=True, maxTime=True)
            sf = start_frame if start_frame is not None else time_range[0]
            ef = end_frame if end_frame is not None else time_range[1]
            cmds.bakeResults(
                target,
                simulation=True,
                t=(sf, ef),
                sampleBy=1,
                oversamplingRate=1,
                disableImplicitControl=True,
                preserveOutsideKeys=False,
                sparseAnimCurveBake=False,
                removeBakedAttributeFromLayer=False,
                removeBakedAnimFromLayer=False,
                bakeOnOverrideLayer=False,
                minimizeRotation=True,
                at=["tx", "ty", "tz", "rx", "ry", "rz"],
            )

        return success_result(
            "Retargeted mocap from '{0}' to '{1}'".format(source, target),
            prompt=(
                "Mocap retargeting complete. "
                "Review the baked animation curves and adjust if needed."
            ),
            source_character=source,
            target_character=target,
            retargeter_node=retargeter,
            baked=bake,
        )
    except Exception as exc:
        return error_result("Failed to retarget mocap", str(exc))
