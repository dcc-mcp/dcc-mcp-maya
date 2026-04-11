"""Delete the construction history on a Maya object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
        ActionResultModel dict with ``context.object_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        cmds.delete(object_name, constructionHistory=True)

        return skill_success(
            "Deleted construction history on '{}'".format(object_name),
            object_name=object_name,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete history for {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`delete_history`."""
    return delete_history(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
