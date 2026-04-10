"""Match transforms of multiple objects to a reference object."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Match translate/rotate/scale of multiple objects to a reference.

    Args:
        params: Dictionary with keys:
            - objects (list[str]): Objects to transform.
            - reference (str): Object to match to.
            - match_translate (bool): Match translation. Default True.
            - match_rotate (bool): Match rotation. Default True.
            - match_scale (bool): Match scale. Default False.

    Returns:
        ActionResultModel with count of matched objects.
    """
    objects = params.get("objects", [])
    reference = params.get("reference", "")
    match_translate = params.get("match_translate", True)
    match_rotate = params.get("match_rotate", True)
    match_scale = params.get("match_scale", False)

    if not objects:
        return error_result("Missing required parameter", "Parameter 'objects' must be a non-empty list")
    if not reference:
        return error_result("Missing required parameter", "Parameter 'reference' is required")

    try:
        if not cmds.objExists(reference):
            return error_result("Object not found", "Reference '{}' does not exist".format(reference))

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Objects not found",
                "The following objects do not exist: {}".format(", ".join(missing)),
            )

        ref_t = cmds.xform(reference, query=True, worldSpace=True, translation=True)
        ref_r = cmds.xform(reference, query=True, worldSpace=True, rotation=True)
        ref_s = cmds.xform(reference, query=True, worldSpace=True, scale=True)

        for obj in objects:
            if match_translate:
                cmds.xform(obj, worldSpace=True, translation=ref_t)
            if match_rotate:
                cmds.xform(obj, worldSpace=True, rotation=ref_r)
            if match_scale:
                cmds.xform(obj, worldSpace=True, scale=ref_s)

        return success_result(
            "Matched {} object(s) to '{}'".format(len(objects), reference),
            prompt="All objects now share the same transform as the reference.",
            reference=reference,
            objects=list(objects),
            count=len(objects),
        )
    except Exception as exc:
        return error_result("Failed to match transforms", str(exc))
