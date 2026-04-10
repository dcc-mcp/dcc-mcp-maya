"""Attach an emitter to an nParticle system or emit from a surface."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

VALID_EMITTER_TYPES = ("omni", "directional", "surface", "curve", "volume")


def emit_particles(
    particle_node: str,
    emitter_type: str = "omni",
    rate: float = 100.0,
    emitter_name: Optional[str] = None,
    source_object: Optional[str] = None,
) -> dict:
    """Create and connect a particle emitter to an nParticle system.

    Args:
        particle_node: Name of the target nParticle object.
        emitter_type: Emitter type — one of ``omni``, ``directional``,
            ``surface``, ``curve``, ``volume``.
        rate: Particles emitted per second.
        emitter_name: Optional name for the emitter node.
        source_object: Optional geometry to emit from (for ``surface``/``curve`` types).

    Returns:
        ActionResultModel dict with ``context.emitter_node`` and ``context.particle_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if emitter_type not in VALID_EMITTER_TYPES:
        return error_result(
            "Invalid emitter type '{}'".format(emitter_type),
            "Valid types: {}".format(", ".join(VALID_EMITTER_TYPES)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(particle_node):
            return error_result(
                "nParticle node not found: '{}'".format(particle_node),
                "Use list_nparticle_systems to see available nodes.",
            ).to_dict()

        emitter_kwargs = {
            "type": emitter_type,
            "rate": rate,
        }
        if emitter_name:
            emitter_kwargs["name"] = emitter_name

        if source_object and emitter_type in ("surface", "curve"):
            if not cmds.objExists(source_object):
                return error_result(
                    "Source object not found: '{}'".format(source_object),
                    "Provide a valid geometry object.",
                ).to_dict()
            emitter_node = cmds.emitter(source_object, **emitter_kwargs)
        else:
            emitter_node = cmds.emitter(**emitter_kwargs)

        if isinstance(emitter_node, (list, tuple)):
            emitter_node = emitter_node[0]

        # Connect emitter to particle system
        cmds.connectDynamic(particle_node, emitters=emitter_node)

        return success_result(
            "Attached emitter '{}' to '{}'".format(emitter_node, particle_node),
            prompt=(
                "Emitter connected. Play the timeline to see particles. "
                "Use set_nparticle_attribute to adjust particle lifespan and behavior."
            ),
            emitter_node=emitter_node,
            particle_node=particle_node,
            emitter_type=emitter_type,
            rate=rate,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("emit_particles failed")
        return error_result("Failed to create particle emitter", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return emit_particles(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(emit_particles("nParticle1")))
