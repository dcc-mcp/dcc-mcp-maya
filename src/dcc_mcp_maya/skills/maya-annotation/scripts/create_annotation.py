"""Create a Maya viewport annotation node."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """Create an annotation node attached to an object or at a world position.

    Args:
        params: Dictionary with keys:
            - text (str): Annotation text.
            - target (str): Object name to attach to. Optional.
            - position (list[float]): [x, y, z] world position. Default [0, 0, 0].
            - name (str): Optional name for the annotation transform.

    Returns:
        ActionResultModel with annotation node name.
    """
    text = params.get("text", "")
    target = params.get("target", "")
    position = params.get("position", [0.0, 0.0, 0.0])
    name = params.get("name", "")

    if not text:
        return error_result("Missing required parameter", "Parameter 'text' is required")

    try:
        pos = list(position)
        if len(pos) < 3:
            pos += [0.0] * (3 - len(pos))

        if target and cmds.objExists(str(target)):
            annotation = cmds.annotate(str(target), text=str(text), point=pos)
        else:
            # Create a locator as base and attach annotation
            loc = cmds.spaceLocator(position=pos)[0]
            annotation = cmds.annotate(loc, text=str(text), point=pos)

        ann_transform = cmds.listRelatives(annotation, parent=True)[0]

        if name:
            ann_transform = cmds.rename(ann_transform, str(name))

        return success_result(
            "Annotation created: '{}'".format(text),
            prompt="Use set_annotation_text to update the annotation text later.",
            annotation_transform=ann_transform,
            text=text,
            position=pos,
        )
    except Exception as exc:
        return error_result("Failed to create annotation", str(exc))
