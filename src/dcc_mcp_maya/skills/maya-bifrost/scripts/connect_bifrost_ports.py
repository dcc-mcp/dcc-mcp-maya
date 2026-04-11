"""Connect output port to input port within a Bifrost graph."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def connect_bifrost_ports(
    graph_node: str,
    source_node_path: str,
    source_port: str,
    target_node_path: str,
    target_port: str,
) -> dict:
    """Connect an output port to an input port in a Bifrost graph.

    Uses the ``vnnConnect`` MEL command to wire ports inside a Bifrost graph
    node.

    Args:
        graph_node: Name of the ``bifrostGraph`` Maya node that contains both
            source and target nodes.
        source_node_path: Graph-internal path to the source compound/node
            (e.g. ``"/get_property"``).
        source_port: Output port name on the source node.
        target_node_path: Graph-internal path to the target compound/node.
        target_port: Input port name on the target node.

    Returns:
        ActionResultModel dict with connection details.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for arg_name, arg_val in [
            ("graph_node", graph_node),
            ("source_node_path", source_node_path),
            ("source_port", source_port),
            ("target_node_path", target_node_path),
            ("target_port", target_port),
        ]:
            if not arg_val:
                return skill_error(
                    "'{}' is required".format(arg_name),
                    "Provide a non-empty value for '{}'".format(arg_name),
                )

        if not cmds.objExists(graph_node):
            return skill_error(
                "Graph '{}' not found".format(graph_node),
                "No node named '{}' exists in the scene".format(graph_node),
            )

        src = "{}.{}".format(source_node_path, source_port)
        dst = "{}.{}".format(target_node_path, target_port)
        cmds.vnnConnect(graph_node, src, dst)

        return skill_success(
            "Connected {}{} → {}{}".format(source_node_path, source_port, target_node_path, target_port),
            prompt="Use set_bifrost_property to adjust node parameters after wiring.",
            graph_node=graph_node,
            source=src,
            target=dst,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to connect Bifrost ports")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_bifrost_ports`."""
    return connect_bifrost_ports(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
