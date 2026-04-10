"""Set a property value on a Bifrost node within a graph."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_bifrost_property(
    graph_node: str,
    node_path: str,
    port_name: str,
    value: object,
) -> dict:
    """Set a port/property value on a Bifrost node inside a graph.

    Uses the ``vnnNode`` MEL command to set a compile-time or default value
    on a Bifrost compound port.

    Args:
        graph_node: Name of the ``bifrostGraph`` Maya node.
        node_path: Graph-internal path to the compound/node
            (e.g. ``"/scatter_points"``).
        port_name: Port name whose value will be changed
            (e.g. ``"point_count"``).
        value: New value for the port.  Numeric and string values are
            supported; lists are joined as a Bifrost vector string.

    Returns:
        ActionResultModel dict with ``context.graph_node``,
        ``context.node_path``, ``context.port_name``, ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for arg_name, arg_val in [
            ("graph_node", graph_node),
            ("node_path", node_path),
            ("port_name", port_name),
        ]:
            if not arg_val:
                return error_result(
                    "'{}' is required".format(arg_name),
                    "Provide a non-empty value for '{}'".format(arg_name),
                ).to_dict()

        if not cmds.objExists(graph_node):
            return error_result(
                "Graph '{}' not found".format(graph_node),
                "No node named '{}' exists in the scene".format(graph_node),
            ).to_dict()

        # Serialise value to string for vnnNode
        if isinstance(value, (list, tuple)):
            str_value = " ".join(str(v) for v in value)
        else:
            str_value = str(value)

        cmds.vnnNode(
            graph_node,
            node_path,
            setPortDefaultValues=[port_name, str_value],
        )

        return success_result(
            "Set {}{}.{} = {}".format(graph_node, node_path, port_name, value),
            prompt="Use list_bifrost_graphs to review the graph structure.",
            graph_node=graph_node,
            node_path=node_path,
            port_name=port_name,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_bifrost_property failed")
        return error_result("Failed to set Bifrost property", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return set_bifrost_property(**kwargs)


if __name__ == "__main__":
    import json

    result = set_bifrost_property("bifrostGraph1", "/scatter_points", "point_count", 1000)
    print(json.dumps(result))
