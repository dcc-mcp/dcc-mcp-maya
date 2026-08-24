"""Delete the construction history on a Maya object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def delete_history(
    object_name: str,
) -> dict:
    """Delete the construction history on a Maya object.

    Equivalent to *Edit > Delete by Type > History* in Maya.  Bakes the
    current deformed state into the mesh and removes all upstream history
    nodes, which can improve scene performance.

    Args:
        object_name: Name of the transform or shape node to process.

    Returns:
        ToolResult dict with ``context.object_name``.
    """

    mutation_applied = False
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        full_shapes = [str(node) for node in (cmds.listRelatives(object_name, shapes=True, fullPath=True) or [])]
        shapes = set(full_shapes)
        shapes.update(node.rsplit("|", 1)[-1] for node in full_shapes)
        history_before = [
            str(node) for node in (cmds.listHistory(object_name) or []) if node != object_name and node not in shapes
        ]
        cmds.delete(object_name, constructionHistory=True)
        mutation_applied = True

        remaining_history = [
            str(node) for node in (cmds.listHistory(object_name) or []) if node != object_name and node not in shapes
        ]
        if remaining_history:
            return skill_error(
                "Delete history verification failed",
                "Maya still reports upstream construction-history nodes",
                object_name=object_name,
                history_before=history_before,
                remaining_history=remaining_history,
                mutation_applied=True,
                rollback_attempted=False,
                rollback_verified=False,
            )

        return skill_success(
            "Deleted construction history on '{}'".format(object_name),
            object_name=object_name,
            removed_history=history_before,
            removed_count=len(history_before),
            remaining_history=[],
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        context = {}
        if mutation_applied:
            context = {
                "mutation_applied": True,
                "rollback_attempted": False,
                "rollback_verified": False,
            }
        return skill_exception(exc, message="Failed to delete history for {}".format(object_name), **context)


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_history`."""
    return delete_history(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
