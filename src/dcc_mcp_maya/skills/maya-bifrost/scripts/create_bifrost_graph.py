"""Create a new Bifrost graph node in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_bifrost_graph(name: Optional[str] = None) -> dict:
    """Create a new empty Bifrost graph node.

    Uses the ``bifrostGraph`` node type introduced in Maya 2019 with the
    Bifrost Extension plugin.  The plugin is loaded on demand.

    Args:
        name: Optional name for the new Bifrost graph node.  If not given
            Maya auto-assigns a name (e.g. ``"bifrostGraph1"``).

    Returns:
        ActionResultModel dict with ``context.graph_node``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Ensure Bifrost plugin is loaded
        if not cmds.pluginInfo("bifrostGraph", query=True, loaded=True):
            cmds.loadPlugin("bifrostGraph")

        create_kwargs = {}
        if name:
            create_kwargs["name"] = name

        graph_node = cmds.createNode("bifrostGraph", **create_kwargs)
        return skill_success(
            "Created Bifrost graph '{}'".format(graph_node),
            prompt="Use add_bifrost_node to add compounds to the graph.",
            graph_node=graph_node,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create Bifrost graph")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_bifrost_graph`."""
    return create_bifrost_graph(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
