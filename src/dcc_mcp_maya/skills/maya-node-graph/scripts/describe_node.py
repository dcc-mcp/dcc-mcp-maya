"""Describe a Maya node with optional attributes and graph connections."""

from __future__ import annotations

from typing import Any, Dict, List

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success, summarize_node, validate_node_exists


def _attr_value(cmds: Any, plug: str) -> Any:
    try:
        value = cmds.getAttr(plug)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], tuple):
        return list(value[0])
    return value


def _attributes(cmds: Any, node: str, limit: int) -> List[Dict[str, Any]]:
    names = cmds.listAttr(node) or []
    attrs = []
    for attr in names[: max(0, int(limit))]:
        plug = "{}.{}".format(node, attr)
        attrs.append(
            {
                "name": str(attr),
                "plug": plug,
                "value": _attr_value(cmds, plug),
            }
        )
    return attrs


def _connections(cmds: Any, node: str) -> List[Dict[str, str]]:
    raw = (
        cmds.listConnections(
            node,
            source=True,
            destination=True,
            plugs=True,
            connections=True,
        )
        or []
    )
    pairs = []
    it = iter(raw)
    for this_plug, other_plug in zip(it, it):
        pairs.append({"plug": str(this_plug), "connected_plug": str(other_plug)})
    return pairs


def describe_node(node_name: str, include_attributes: bool = False, include_connections: bool = True) -> dict:
    """Return a compact node identity packet plus optional graph details."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, node_name)
        if err:
            return err
        summary = summarize_node(cmds, node_name)
        payload = {
            "node": summary,
            "node_name": summary.get("long_name", node_name),
            "node_type": summary.get("object_type"),
        }
        if include_attributes:
            payload["attributes"] = _attributes(cmds, node_name, 200)
        if include_connections:
            payload["connections"] = _connections(cmds, node_name)

        return maya_success(
            "Described node: {}".format(node_name),
            **payload,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to describe Maya node")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`describe_node`."""
    return describe_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
