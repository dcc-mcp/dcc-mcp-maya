"""Create a new Bifrost graph node in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Ensure Bifrost plugin is loaded
        if not cmds.pluginInfo("bifrostGraph", query=True, loaded=True):
            cmds.loadPlugin("bifrostGraph")

        create_kwargs = {}
        if name:
            create_kwargs["name"] = name

        graph_node = cmds.createNode("bifrostGraph", **create_kwargs)
        return success_result(
            "Created Bifrost graph '{}'".format(graph_node),
            prompt="Use add_bifrost_node to add compounds to the graph.",
            graph_node=graph_node,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_bifrost_graph failed")
        return error_result("Failed to create Bifrost graph", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_bifrost_graph(**kwargs)


if __name__ == "__main__":
    import json

    result = create_bifrost_graph()
    print(json.dumps(result))
