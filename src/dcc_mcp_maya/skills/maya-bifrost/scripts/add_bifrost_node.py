"""Add a typed node to an existing Bifrost graph."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import add_node, compound_node_path, ensure_bifrost_plugins, normalize_compound_path


def add_bifrost_node(
    graph: str,
    node_type: str,
    name: Optional[str] = None,
    compound: str = ".",
) -> dict:
    """Add a node such as ``Modeling::Primitive::create_mesh_cube``."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        compound_path = normalize_compound_path(compound)
        node = add_node(cmds, graph, node_type, name=name, compound=compound_path)
        ports = [
            str(port) for port in (cmds.vnnNode(graph, compound_node_path(compound_path, node), listPorts=True) or [])
        ]
        return maya_success(
            "Added Bifrost node: {}".format(node),
            graph=graph,
            node=node,
            node_type=node_type,
            compound=compound_path,
            ports=ports,
            runtime=runtime,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to add Bifrost node")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`add_bifrost_node`."""
    return add_bifrost_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
