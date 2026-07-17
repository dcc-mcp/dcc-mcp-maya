"""Create a Bifrost graph shape or board in the current Maya scene."""

from __future__ import annotations

from typing import Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.bifrost import create_graph, ensure_bifrost_plugins


def create_bifrost_graph(name: Optional[str] = None, kind: str = "graph_shape") -> dict:
    """Create an empty Bifrost graph container."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        runtime = ensure_bifrost_plugins(cmds)
        graph = create_graph(cmds, name=name, kind=str(kind))
        return maya_success("Created Bifrost {}: {}".format(kind, graph["graph"]), runtime=runtime, **graph)
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create Bifrost graph")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_bifrost_graph`."""
    return create_bifrost_graph(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
