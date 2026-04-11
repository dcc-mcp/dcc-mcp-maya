"""List connections to/from a given Maya node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def list_node_connections(
    node_name: str,
    direction: str = "both",
    plugs: bool = True,
) -> dict:
    """List incoming and/or outgoing attribute connections for a node.

    Args:
        node_name: Name of the node to inspect.
        direction: ``"incoming"`` | ``"outgoing"`` | ``"both"``. Default ``"both"``.
        plugs: Whether to include plug names (not just node names). Default True.

    Returns:
        ActionResultModel dict with ``context.connections`` list of
        ``{"source": ..., "destination": ...}`` dicts.
    """

    if not node_name:
        return skill_error("No node provided", "Provide 'node_name' parameter.")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node_name)
        if err:
            return err

        connections = []

        if direction in ("incoming", "both"):
            raw = cmds.listConnections(node_name, source=True, destination=False, plugs=plugs, connections=plugs) or []
            if plugs:
                for i in range(0, len(raw) - 1, 2):
                    connections.append({"source": raw[i + 1], "destination": raw[i]})
            else:
                for src in raw:
                    connections.append({"source": src, "destination": node_name})

        if direction in ("outgoing", "both"):
            raw = cmds.listConnections(node_name, source=False, destination=True, plugs=plugs, connections=plugs) or []
            if plugs:
                for i in range(0, len(raw) - 1, 2):
                    connections.append({"source": raw[i], "destination": raw[i + 1]})
            else:
                for dst in raw:
                    connections.append({"source": node_name, "destination": dst})

        return skill_success(
            "{} connections found for '{}'".format(len(connections), node_name),
            prompt=("Connections listed. Use connectAttr / disconnectAttr actions to modify the shading network."),
            connections=connections,
            count=len(connections),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list connections")


@skill_entry
def main(**kwargs):
    return list_node_connections(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
