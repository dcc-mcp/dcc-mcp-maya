"""List all Bifrost graph nodes in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_bifrost_graphs() -> dict:
    """List all ``bifrostGraph`` nodes present in the scene.

    Returns:
        ActionResultModel dict with ``context.graphs`` (list of node names)
        and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        graphs = cmds.ls(type="bifrostGraph") or []
        return success_result(
            "Found {} Bifrost graph(s)".format(len(graphs)),
            prompt="Use add_bifrost_node to add compounds or connect_bifrost_ports to wire ports.",
            graphs=graphs,
            count=len(graphs),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_bifrost_graphs failed")
        return error_result("Failed to list Bifrost graphs", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_bifrost_graphs`."""
    return list_bifrost_graphs(**kwargs)


if __name__ == "__main__":
    import json

    result = list_bifrost_graphs()
    print(json.dumps(result))
