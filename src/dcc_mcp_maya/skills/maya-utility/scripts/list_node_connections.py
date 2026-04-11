"""List connections to/from a given Maya node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

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

    if not node:
        return maya_error("No node provided", "Provide 'node' parameter.")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node):
            return maya_error("Node not found", "No node named '{}'.".format(node))

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

        return maya_success(
            "{} connections found for '{}'".format(len(connections), node),
            prompt=("Connections listed. Use connectAttr / disconnectAttr actions to modify the shading network."),
            connections=connections,
            count=len(connections),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to list connections")

def main(**kwargs):
    return list_node_connections(**kwargs)

if __name__ == "__main__":
    import json

    result = list_node_connections("lambert1")
    print(json.dumps(result))
