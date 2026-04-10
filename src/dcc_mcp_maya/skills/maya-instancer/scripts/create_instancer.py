"""Create a Particle Instancer node."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Create a Particle Instancer and attach instance objects.

    Args:
        params: Dictionary containing:
            - particle_system (str): Name of the particle/nParticle object. Required.
            - instance_objects (list[str]): List of objects to instance. Required.
            - name (str): Optional name for the instancer node.
            - cycle (str): Cycle mode: 'None', 'Sequential', 'Random'. Default 'None'.

    Returns:
        ActionResultModel with the instancer node name.
    """
    particle_system = params.get("particle_system", "")
    instance_objects: List[str] = list(params.get("instance_objects") or [])  # type: ignore[arg-type]
    name = params.get("name", "")
    cycle = params.get("cycle", "None")

    if not particle_system:
        return error_result("Invalid parameters", "Parameter 'particle_system' is required.")
    if not instance_objects:
        return error_result("Invalid parameters", "Parameter 'instance_objects' must be a non-empty list.")

    cycle_modes = {"None": 0, "Sequential": 1, "Random": 2}
    cycle_index = cycle_modes.get(str(cycle), 0)

    try:
        if not cmds.objExists(particle_system):
            return error_result(
                "Particle system not found",
                "No object named '{}' in the scene.".format(particle_system),
            )
        kwargs: Dict[str, object] = {"object": instance_objects, "cycle": cycle_index}
        if name:
            kwargs["name"] = name
        instancer_nodes = cmds.particleInstancer(particle_system, **kwargs)
        instancer_name = instancer_nodes[0] if isinstance(instancer_nodes, (list, tuple)) else instancer_nodes
        return success_result(
            "Created particle instancer '{}'".format(instancer_name),
            prompt="Use set_instancer_attribute to adjust cycling, rotation, or scale modes.",
            instancer=instancer_name,
            particle_system=particle_system,
            instance_objects=instance_objects,
        )
    except Exception as exc:
        return error_result("Failed to create particle instancer", str(exc))
