"""List nodes/attributes connected to a Maya node or attribute."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def list_connections(
    object_name: str,
    attribute: Optional[str] = None,
    incoming: bool = True,
    outgoing: bool = True,
) -> dict:
    """List nodes/attributes connected to a Maya node or attribute.

    Args:
        object_name: Name of the Maya node to inspect.
        attribute: If specified, inspect connections on this specific
            attribute (e.g. ``"translateX"``).  If None, inspect all
            connections on the node.
        incoming: Include incoming connections.  Default: True.
        outgoing: Include outgoing connections.  Default: True.

    Returns:
        ToolResult dict with ``context.connections`` — a list of
        connected attribute path strings, and ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        query_target = "{}.{}".format(object_name, attribute) if attribute else object_name
        if attribute and not cmds.objExists(query_target):
            return skill_error(
                "Attribute not found: {}".format(query_target),
                "The attribute '{}' does not exist on '{}'".format(attribute, object_name),
            )

        connections = (
            cmds.listConnections(
                query_target,
                source=incoming,
                destination=outgoing,
                plugs=True,
                connections=True,
            )
            or []
        )

        # listConnections returns alternating pairs [src, dst, src, dst, ...]
        # Flatten into a list of connection dicts
        pairs = []
        it = iter(connections)
        for a, b in zip(it, it):
            pairs.append({"from": a, "to": b})

        return skill_success(
            "Found {} connection(s) on '{}'".format(len(pairs), query_target),
            object_name=object_name,
            attribute=attribute,
            connections=pairs,
            count=len(pairs),
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list connections on {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_connections`."""
    return list_connections(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
