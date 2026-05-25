"""Create and optionally connect a Maya gravity field."""

from __future__ import annotations

from typing import Any, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _as_vector(value: Optional[List[float]], default: List[float], name: str) -> List[float]:
    vector = default if value is None else value
    if len(vector) != 3:
        raise ValueError("{} must contain exactly three numbers".format(name))
    return [float(vector[0]), float(vector[1]), float(vector[2])]


def _normalise_created_nodes(result: Any) -> List[str]:
    if result is None:
        return []
    if isinstance(result, (list, tuple)):
        return [str(item) for item in result]
    return [str(result)]


def _pick_field_node(cmds: Any, nodes: List[str]) -> Optional[str]:
    for node in nodes:
        try:
            node_type = str(cmds.nodeType(node))
        except Exception:  # noqa: BLE001
            node_type = ""
        if node_type.lower().endswith("field"):
            return node
    return nodes[-1] if nodes else None


def create_gravity_field(
    name: str = "mcp_gravity",
    magnitude: float = 9.8,
    direction: Optional[List[float]] = None,
    attenuation: float = 0.0,
    position: Optional[List[float]] = None,
    targets: Optional[List[str]] = None,
    connect: bool = True,
) -> dict:
    """Create a gravity field and optionally connect it to dynamic targets."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        target_nodes = _as_list(targets)
        if target_nodes:
            err = batch_validate_nodes(cmds, target_nodes)
            if err:
                return err

        dx, dy, dz = _as_vector(direction, [0.0, -1.0, 0.0], "direction")
        kwargs = {
            "name": str(name),
            "magnitude": float(magnitude),
            "attenuation": float(attenuation),
            "directionX": dx,
            "directionY": dy,
            "directionZ": dz,
        }
        if position is not None:
            kwargs["position"] = _as_vector(position, [0.0, 0.0, 0.0], "position")

        created_nodes = _normalise_created_nodes(cmds.gravity(**kwargs))
        field_node = _pick_field_node(cmds, created_nodes)
        connected_targets: List[str] = []
        if connect and target_nodes and field_node:
            cmds.connectDynamic(target_nodes, fields=field_node)
            connected_targets = target_nodes

        return maya_success(
            "Created gravity field: {}".format(field_node or str(name)),
            field=field_node,
            created_nodes=created_nodes,
            connected_targets=connected_targets,
            settings={
                "name": str(name),
                "magnitude": float(magnitude),
                "direction": [dx, dy, dz],
                "attenuation": float(attenuation),
                "position": kwargs.get("position"),
            },
            prompt="Use make_rigid_body first for targets that are not dynamic yet.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create gravity field")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_gravity_field`."""
    return create_gravity_field(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
