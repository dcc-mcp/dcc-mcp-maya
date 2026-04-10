"""Change the text or position of an existing annotation."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def update_annotation(
    annotation_node: str,
    text: Optional[str] = None,
    position: Optional[List[float]] = None,
) -> dict:
    """Update the text or position of an existing annotation node.

    Args:
        annotation_node: Name of the annotation shape node (``annotationShape``).
            Can also be the transform node — its shape will be located automatically.
        text: New text content.  If None, the text is unchanged.
        position: New ``[x, y, z]`` world-space position for the transform.
            If None, the position is unchanged.

    Returns:
        ActionResultModel dict with ``context.annotation_node`` and
        updated ``context.text`` / ``context.position``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(annotation_node):
            return error_result(
                "Annotation not found: {}".format(annotation_node),
                "'{}' does not exist".format(annotation_node),
            ).to_dict()

        node_type = cmds.objectType(annotation_node)
        if node_type != "annotationShape":
            shapes = cmds.listRelatives(annotation_node, shapes=True, type="annotationShape") or []
            if not shapes:
                return error_result(
                    "No annotationShape found under '{}'".format(annotation_node),
                    "Provide the annotationShape node name directly.",
                ).to_dict()
            annotation_node = shapes[0]

        parents = cmds.listRelatives(annotation_node, parent=True)
        transform_node = parents[0] if parents else None

        if text is not None:
            cmds.setAttr("{}.text".format(annotation_node), text, type="string")

        if position and len(position) == 3 and transform_node:
            cmds.move(position[0], position[1], position[2], transform_node, absolute=True)

        current_text = cmds.getAttr("{}.text".format(annotation_node)) or ""
        return success_result(
            "Updated annotation '{}'".format(current_text[:40]),
            prompt="Use list_annotations to verify the update.",
            annotation_node=annotation_node,
            transform_node=transform_node,
            text=current_text,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("update_annotation failed")
        return error_result("Failed to update annotation", str(exc)).to_dict()


def main(**kwargs):
    return update_annotation(**kwargs)


if __name__ == "__main__":
    import json

    result = update_annotation("annotationShape1", text="Updated text")
    print(json.dumps(result))
