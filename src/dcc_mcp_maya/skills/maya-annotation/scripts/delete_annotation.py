"""Delete an annotation node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def delete_annotation(annotation_node: str) -> dict:
    """Delete an annotation node from the scene.

    Deletes both the annotationShape and its parent transform node.

    Args:
        annotation_node: Name of the annotation shape or transform node to delete.

    Returns:
        ActionResultModel dict with ``context.deleted_node``.
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
        if node_type == "annotationShape":
            parents = cmds.listRelatives(annotation_node, parent=True)
            to_delete = parents[0] if parents else annotation_node
        else:
            to_delete = annotation_node

        cmds.delete(to_delete)

        return success_result(
            "Deleted annotation '{}'".format(annotation_node),
            prompt="Use list_annotations to confirm deletion.",
            deleted_node=annotation_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_annotation failed")
        return error_result("Failed to delete annotation", str(exc)).to_dict()


def main(**kwargs):
    return delete_annotation(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_annotation("annotationShape1")
    print(json.dumps(result))
