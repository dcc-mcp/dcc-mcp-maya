"""Delete an annotation node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def delete_annotation(annotation_node: str) -> dict:
    """Delete an annotation node from the scene.

    Deletes both the annotationShape and its parent transform node.

    Args:
        annotation_node: Name of the annotation shape or transform node to delete.

    Returns:
        ActionResultModel dict with ``context.deleted_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(annotation_node):
            return maya_error(
                "Annotation not found: {}".format(annotation_node),
                "'{}' does not exist".format(annotation_node),
            )

        node_type = cmds.objectType(annotation_node)
        if node_type == "annotationShape":
            parents = cmds.listRelatives(annotation_node, parent=True)
            to_delete = parents[0] if parents else annotation_node
        else:
            to_delete = annotation_node

        cmds.delete(to_delete)

        return maya_success(
            "Deleted annotation '{}'".format(annotation_node),
            prompt="Use list_annotations to confirm deletion.",
            deleted_node=annotation_node,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to delete annotation")


def main(**kwargs):
    return delete_annotation(**kwargs)


if __name__ == "__main__":
    import json

    result = delete_annotation("annotationShape1")
    print(json.dumps(result))
