"""List connections to/from a given Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_node_connections(
    node: str,
    direction: str = "both",
    plugs: bool = True,
) -> dict:
    """List incoming and/or outgoing attribute connections for a node.

    Args:
        node: Name of the node to inspect.
        direction: ``"incoming"`` | ``"outgoing"`` | ``"both"``. Default ``"both"``.
        plugs: Whether to include plug names (not just node names). Default True.

    Returns:
        ActionResultModel dict with ``context.connections`` list of
        ``{"source": ..., "destination": ...}`` dicts.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not node:
        return error_result("No node provided", "Provide 'node' parameter.").to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node):
            return error_result("Node not found", "No node named '{}'.".format(node)).to_dict()

        connections = []

        if direction in ("incoming", "both"):
            raw = cmds.listConnections(node, source=True, destination=False, plugs=plugs, connections=plugs) or []
            if plugs:
                for i in range(0, len(raw) - 1, 2):
                    connections.append({"source": raw[i + 1], "destination": raw[i]})
            else:
                for src in raw:
                    connections.append({"source": src, "destination": node})

        if direction in ("outgoing", "both"):
            raw = cmds.listConnections(node, source=False, destination=True, plugs=plugs, connections=plugs) or []
            if plugs:
                for i in range(0, len(raw) - 1, 2):
                    connections.append({"source": raw[i], "destination": raw[i + 1]})
            else:
                for dst in raw:
                    connections.append({"source": node, "destination": dst})

        return success_result(
            "{} connections found for '{}'".format(len(connections), node),
            prompt=("Connections listed. Use connectAttr / disconnectAttr actions to modify the shading network."),
            connections=connections,
            count=len(connections),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_node_connections failed")
        return error_result("Failed to list connections", str(exc)).to_dict()


def main(**kwargs):
    return list_node_connections(**kwargs)


if __name__ == "__main__":
    import json

    result = list_node_connections("lambert1")
    print(json.dumps(result))
