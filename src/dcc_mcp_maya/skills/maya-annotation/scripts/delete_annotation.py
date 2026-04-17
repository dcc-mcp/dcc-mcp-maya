"""Delete an annotation node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_annotation(annotation_node: str) -> dict:
    """Delete an annotation node from the scene.

    Deletes both the annotationShape and its parent transform node.

    Args:
        annotation_node: Name of the annotation shape or transform node to delete.

    Returns:
        ToolResult dict with ``context.deleted_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, annotation_node)
        if err:
            return err

        node_type = cmds.objectType(annotation_node)
        if node_type == "annotationShape":
            parents = cmds.listRelatives(annotation_node, parent=True)
            to_delete = parents[0] if parents else annotation_node
        else:
            to_delete = annotation_node

        cmds.delete(to_delete)

        return skill_success(
            "Deleted annotation '{}'".format(annotation_node),
            prompt="Use list_annotations to confirm deletion.",
            deleted_node=annotation_node,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete annotation")


@skill_entry
def main(**kwargs):
    return delete_annotation(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
