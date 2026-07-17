"""List Bifrost graph shapes, boards, nodes, and optional ports."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import ensure_bifrost_plugins, list_graphs


def list_bifrost_graphs(include_nodes: bool = True, include_ports: bool = False) -> dict:
    """Inspect Bifrost graphs in the current Maya scene."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        graphs = list_graphs(cmds, include_nodes=bool(include_nodes), include_ports=bool(include_ports))
        return maya_success(
            "Found {} Bifrost graph(s)".format(len(graphs)),
            graphs=graphs,
            count=len(graphs),
            runtime=runtime,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list Bifrost graphs")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_bifrost_graphs`."""
    return list_bifrost_graphs(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
