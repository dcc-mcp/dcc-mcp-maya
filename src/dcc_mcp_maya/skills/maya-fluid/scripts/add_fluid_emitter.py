"""Add a fluid emitter to a Maya Fluid container."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def add_fluid_emitter(
    fluid_node: str,
    emitter_name: Optional[str] = None,
    emitter_type: str = "omni",
    rate: float = 100.0,
    density_rate: float = 1.0,
) -> dict:
    """Add a fluid emitter to an existing Fluid Effects container.

    Args:
        fluid_node: Name of the fluidShape or its parent transform.
        emitter_name: Optional name for the new emitter node.
        emitter_type: Emitter type — ``"omni"``, ``"directional"``, or ``"volume"``.
        rate: Emission rate (particles/second or voxels/second for fluid).
        density_rate: Density emission rate (0–1 per second).

    Returns:
        ActionResultModel dict with ``context.emitter_node`` and ``context.fluid_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not fluid_node:
        return error_result("No fluid node specified", "Provide a fluidShape or transform name.").to_dict()

    valid_types = ("omni", "directional", "volume")
    if emitter_type not in valid_types:
        return error_result(
            "Invalid emitter_type '{}'".format(emitter_type),
            "Supported types: {}".format(", ".join(valid_types)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(fluid_node):
            return error_result(
                "Fluid node '{}' does not exist".format(fluid_node),
                "Check the node name with list_fluid_containers.",
            ).to_dict()

        # Resolve to shape if transform was passed
        node_type = cmds.objectType(fluid_node)
        if node_type != "fluidShape":
            shapes = cmds.listRelatives(fluid_node, shapes=True, type="fluidShape") or []
            if not shapes:
                return error_result(
                    "'{}' has no fluidShape child".format(fluid_node),
                    "Provide a valid fluid container.",
                ).to_dict()
            fluid_shape = shapes[0]
        else:
            fluid_shape = fluid_node

        emit_kwargs = {
            "fluidDropoff": 2.0,
            "fluidDensityEmission": density_rate,
            "rate": rate,
            "type": emitter_type,
        }
        if emitter_name:
            emit_kwargs["name"] = emitter_name

        emitter_node = cmds.fluidEmitter(fluid_shape, **emit_kwargs)

        return success_result(
            "Added {} emitter '{}' to fluid container '{}'".format(emitter_type, emitter_node, fluid_node),
            prompt=(
                "Emitter added. Use set_fluid_attribute to tune density/temperature, "
                "or simulate the scene to see the fluid emission."
            ),
            emitter_node=emitter_node,
            fluid_node=fluid_node,
            emitter_type=emitter_type,
            rate=rate,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_fluid_emitter failed")
        return error_result("Failed to add fluid emitter", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return add_fluid_emitter(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(add_fluid_emitter("fluidShape1")))
