"""Bake world-space transforms for a list of objects over a frame range."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Bake world-space TRS transforms for objects onto local channels.

    Args:
        params: Dictionary with keys:
            - objects (list[str]): Object names to bake.
            - start_frame (float): Start frame. Default current timeline start.
            - end_frame (float): End frame. Default current timeline end.
            - sample_by (float): Key every N frames. Default 1.0.

    Returns:
        ActionResultModel with baked object count.
    """
    objects = params.get("objects", [])
    sample_by = params.get("sample_by", 1.0)

    if not objects:
        return error_result("Missing required parameter", "Parameter 'objects' must be a non-empty list")

    try:
        start_frame = params.get("start_frame", cmds.playbackOptions(query=True, minTime=True))
        end_frame = params.get("end_frame", cmds.playbackOptions(query=True, maxTime=True))

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Objects not found",
                "The following objects do not exist: {}".format(", ".join(missing)),
            )

        cmds.bakeResults(
            objects,
            simulation=True,
            t=(start_frame, end_frame),
            sampleBy=sample_by,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            attribute=["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"],
        )

        return success_result(
            "Baked world transforms for {} object(s) [{} - {}]".format(
                len(objects), start_frame, end_frame
            ),
            prompt="Transforms are baked. You can now delete constraints or parent nodes safely.",
            objects=list(objects),
            start_frame=start_frame,
            end_frame=end_frame,
            count=len(objects),
        )
    except Exception as exc:
        return error_result("Failed to bake transforms", str(exc))
