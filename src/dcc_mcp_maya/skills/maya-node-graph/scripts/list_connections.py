"""List nodes/attributes connected to a Maya node or attribute."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
        ActionResultModel dict with ``context.connections`` — a list of
        connected attribute path strings, and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        query_target = "{}.{}".format(object_name, attribute) if attribute else object_name
        if attribute and not cmds.objExists(query_target):
            return error_result(
                "Attribute not found: {}".format(query_target),
                "The attribute '{}' does not exist on '{}'".format(attribute, object_name),
            ).to_dict()

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

        return success_result(
            "Found {} connection(s) on '{}'".format(len(pairs), query_target),
            object_name=object_name,
            attribute=attribute,
            connections=pairs,
            count=len(pairs),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_connections failed")
        return error_result("Failed to list connections on {}".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return list_connections(**kwargs)


if __name__ == "__main__":
    import json

    result = list_connections()
    print(json.dumps(result))
