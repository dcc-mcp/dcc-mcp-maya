"""Set a property value on a Bifrost node within a graph."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
        ToolResult dict with ``context.graph_node``,
        ``context.node_path``, ``context.port_name``, ``context.value``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for arg_name, arg_val in [
            ("graph_node", graph_node),
            ("node_path", node_path),
            ("port_name", port_name),
        ]:
            if not arg_val:
                return skill_error(
                    "'{}' is required".format(arg_name),
                    "Provide a non-empty value for '{}'".format(arg_name),
                )

        err = validate_node_exists(cmds, graph_node)
        if err:
            return err

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

        return skill_success(
            "Set {}{}.{} = {}".format(graph_node, node_path, port_name, value),
            prompt="Use list_bifrost_graphs to review the graph structure.",
            graph_node=graph_node,
            node_path=node_path,
            port_name=port_name,
            value=value,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set Bifrost property")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_bifrost_property`."""
    return set_bifrost_property(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
