"""Add a Bifrost compound/node to an existing Bifrost graph."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def add_bifrost_node(graph_node: str, compound_name: str) -> dict:
    """Add a Bifrost compound to an existing graph node.

    Uses the ``vnnCompound`` command (available when the ``bifrostGraph``
    plugin is loaded) to instantiate a named compound inside the graph.

    Args:
        graph_node: Name of the target ``bifrostGraph`` Maya node.
        compound_name: Fully-qualified Bifrost compound path, e.g.
            ``"Bifrost::Object::get_property"`` or a short alias accepted by
            the installed Bifrost library.

    Returns:
        ActionResultModel dict with ``context.graph_node``,
        ``context.compound_name``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not graph_node:
            return skill_error("graph_node is required", "Provide the name of a bifrostGraph node")
        if not compound_name:
            return skill_error("compound_name is required", "Provide a Bifrost compound path")

        if not cmds.objExists(graph_node):
            return skill_error(
                "Graph '{}' not found".format(graph_node),
                "No node named '{}' exists in the scene".format(graph_node),
            )

        if cmds.objectType(graph_node) != "bifrostGraph":
            return skill_error(
                "'{}' is not a bifrostGraph node".format(graph_node),
                "The node must be of type 'bifrostGraph'",
            )

        # Use the vnnCompound MEL command to add the compound
        cmds.vnnCompound(graph_node, "/", addNode=compound_name)
        return skill_success(
            "Added compound '{}' to graph '{}'".format(compound_name, graph_node),
            prompt="Use connect_bifrost_ports to wire the compound ports to other nodes.",
            graph_node=graph_node,
            compound_name=compound_name,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add Bifrost node")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_bifrost_node`."""
    return add_bifrost_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
