"""Add a Bifrost compound/node to an existing Bifrost graph."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not graph_node:
            return error_result("graph_node is required", "Provide the name of a bifrostGraph node").to_dict()
        if not compound_name:
            return error_result("compound_name is required", "Provide a Bifrost compound path").to_dict()

        if not cmds.objExists(graph_node):
            return error_result(
                "Graph '{}' not found".format(graph_node),
                "No node named '{}' exists in the scene".format(graph_node),
            ).to_dict()

        if cmds.objectType(graph_node) != "bifrostGraph":
            return error_result(
                "'{}' is not a bifrostGraph node".format(graph_node),
                "The node must be of type 'bifrostGraph'",
            ).to_dict()

        # Use the vnnCompound MEL command to add the compound
        cmds.vnnCompound(graph_node, "/", addNode=compound_name)
        return success_result(
            "Added compound '{}' to graph '{}'".format(compound_name, graph_node),
            prompt="Use connect_bifrost_ports to wire the compound ports to other nodes.",
            graph_node=graph_node,
            compound_name=compound_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_bifrost_node failed")
        return error_result("Failed to add Bifrost node", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return add_bifrost_node(**kwargs)


if __name__ == "__main__":
    import json

    result = add_bifrost_node("bifrostGraph1", "Bifrost::Object::get_property")
    print(json.dumps(result))
