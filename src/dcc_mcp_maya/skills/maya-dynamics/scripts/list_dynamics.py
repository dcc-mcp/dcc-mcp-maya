"""List Maya classic dynamics nodes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

FIELD_NODE_TYPES = (
    "airField",
    "dragField",
    "gravityField",
    "newtonField",
    "radialField",
    "turbulenceField",
    "uniformField",
    "vortexField",
    "volumeAxisField",
)

RIGID_BODY_ATTRS = (
    "active",
    "mass",
    "bounciness",
    "damping",
    "staticFriction",
    "dynamicFriction",
    "collisions",
    "ignore",
)

FIELD_ATTRS = (
    "magnitude",
    "attenuation",
    "directionX",
    "directionY",
    "directionZ",
    "maxDistance",
)


def _safe_ls_type(cmds: Any, node_type: str) -> List[str]:
    try:
        return [str(node) for node in (cmds.ls(type=node_type) or [])]
    except Exception:  # noqa: BLE001
        return []


def _safe_node_type(cmds: Any, node: str) -> Optional[str]:
    for method_name in ("nodeType", "objectType"):
        method = getattr(cmds, method_name, None)
        if not callable(method):
            continue
        try:
            return str(method(node))
        except Exception:  # noqa: BLE001
            continue
    return None


def _safe_get_attr(cmds: Any, node: str, attr: str) -> Any:
    plug = "{}.{}".format(node, attr)
    try:
        exists = getattr(cmds, "objExists", None)
        if callable(exists) and not exists(plug):
            return None
    except Exception:  # noqa: BLE001
        pass
    try:
        value = cmds.getAttr(plug)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], tuple):
        return list(value[0])
    return value


def _safe_connections(cmds: Any, node: str) -> List[str]:
    try:
        return [str(item) for item in (cmds.listConnections(node, source=True, destination=True) or [])]
    except Exception:  # noqa: BLE001
        return []


def _node_payload(cmds: Any, node: str, attrs: tuple[str, ...], include_connections: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": node,
        "node_type": _safe_node_type(cmds, node),
    }
    values = {attr: _safe_get_attr(cmds, node, attr) for attr in attrs}
    payload["attrs"] = {key: value for key, value in values.items() if value is not None}
    if include_connections:
        payload["connections"] = _safe_connections(cmds, node)
    return payload


def list_dynamics(include_connections: bool = True) -> dict:
    """List rigid body and field nodes in the current Maya scene."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        rigid_bodies = _safe_ls_type(cmds, "rigidBody")
        fields: List[str] = []
        for node_type in FIELD_NODE_TYPES:
            fields.extend(_safe_ls_type(cmds, node_type))
        constraints = _safe_ls_type(cmds, "rigidConstraint")

        return maya_success(
            "Found {} rigid body node(s), {} field node(s), and {} rigid constraint(s)".format(
                len(rigid_bodies),
                len(fields),
                len(constraints),
            ),
            rigid_bodies=[
                _node_payload(cmds, node, RIGID_BODY_ATTRS, bool(include_connections)) for node in rigid_bodies
            ],
            fields=[_node_payload(cmds, node, FIELD_ATTRS, bool(include_connections)) for node in fields],
            constraints=[_node_payload(cmds, node, tuple(), bool(include_connections)) for node in constraints],
            counts={
                "rigid_bodies": len(rigid_bodies),
                "fields": len(fields),
                "constraints": len(constraints),
            },
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list dynamics nodes")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_dynamics`."""
    return list_dynamics(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
