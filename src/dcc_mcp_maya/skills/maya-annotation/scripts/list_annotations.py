"""List all annotation nodes in the current scene."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]):
    """List all annotationShape nodes with their text and world position.

    Args:
        params: Dictionary with keys:
            - include_text (bool): Whether to include text content. Default True.

    Returns:
        ActionResultModel with list of annotation info dicts.
    """
    include_text = params.get("include_text", True)

    try:
        shapes = cmds.ls(type="annotationShape") or []
        annotations: List[Dict[str, object]] = []

        for shape in shapes:
            info: Dict[str, object] = {"shape": shape}
            parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
            info["transform"] = parents[0] if parents else ""

            if include_text:
                try:
                    info["text"] = cmds.getAttr("{}.text".format(shape))
                except Exception:
                    info["text"] = ""

            annotations.append(info)

        return success_result(
            "Found {} annotation(s)".format(len(annotations)),
            prompt="Use set_annotation_text to update or delete_annotation to remove annotations.",
            annotations=annotations,
            count=len(annotations),
        )
    except Exception as exc:
        return error_result("Failed to list annotations", str(exc))
