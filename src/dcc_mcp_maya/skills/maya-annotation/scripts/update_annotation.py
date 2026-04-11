"""Change the text or position of an existing annotation."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, annotation_node)
        if err:
            return err

        node_type = cmds.objectType(annotation_node)
        if node_type != "annotationShape":
            shapes = cmds.listRelatives(annotation_node, shapes=True, type="annotationShape") or []
            if not shapes:
                return skill_error(
                    "No annotationShape found under '{}'".format(annotation_node),
                    "Provide the annotationShape node name directly.",
                )
            annotation_node = shapes[0]

        parents = cmds.listRelatives(annotation_node, parent=True)
        transform_node = parents[0] if parents else None

        if text is not None:
            cmds.setAttr("{}.text".format(annotation_node), text, type="string")

        if position and len(position) == 3 and transform_node:
            cmds.move(position[0], position[1], position[2], transform_node, absolute=True)

        current_text = cmds.getAttr("{}.text".format(annotation_node)) or ""
        return skill_success(
            "Updated annotation '{}'".format(current_text[:40]),
            prompt="Use list_annotations to verify the update.",
            annotation_node=annotation_node,
            transform_node=transform_node,
            text=current_text,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to update annotation")


@skill_entry
def main(**kwargs):
    return update_annotation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
