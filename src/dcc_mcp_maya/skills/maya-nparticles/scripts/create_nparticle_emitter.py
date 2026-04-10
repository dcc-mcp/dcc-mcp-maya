"""Create an nParticle emitter attached to a nucleus solver."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_nparticle_emitter(
    name: str = "nParticle1",
    emitter_type: str = "omni",
    rate: float = 100.0,
    speed: float = 1.0,
    position: Optional[list] = None,
    nucleus: Optional[str] = None,
) -> dict:
    """Create an nParticle system with an emitter and nucleus solver.

    Args:
        name: Base name for the nParticle shape node.
        emitter_type: Emitter type — ``"omni"``, ``"directional"``, or
            ``"volume"``.  Default: ``"omni"``.
        rate: Particle emission rate (particles per second).  Default: 100.
        speed: Initial particle speed.  Default: 1.0.
        position: ``[x, y, z]`` emitter position.  Default: world origin.
        nucleus: Existing nucleus node to attach to.  If None, the default
            nucleus created by Maya is used.

    Returns:
        ActionResultModel dict with particle shape, emitter, and nucleus names.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        pos = position if position and len(position) == 3 else [0.0, 0.0, 0.0]

        # Create nParticle via MEL (handles nucleus wiring automatically)
        mel.eval("nParticle;")

        # Get the last created nParticle shape
        particle_shapes = cmds.ls(type="nParticle") or []
        if not particle_shapes:
            return error_result(
                "Failed to create nParticle",
                "No nParticle node found after creation",
            ).to_dict()
        particle_shape = particle_shapes[-1]

        # Get emitter connected to the particle shape
        emitters = cmds.listConnections(particle_shape, type="pointEmitter") or []
        emitter_node = emitters[0] if emitters else None

        # Rename particle transform
        particle_transform = cmds.listRelatives(particle_shape, parent=True)[0]
        try:
            particle_transform = cmds.rename(particle_transform, name)
            particle_shape = cmds.listRelatives(particle_transform, shapes=True)[0]
        except Exception:
            pass

        # Configure emitter
        if emitter_node:
            cmds.setAttr("{}.emitterType".format(emitter_node),
                         {"omni": 0, "directional": 1, "volume": 3}.get(emitter_type, 0))
            cmds.setAttr("{}.rate".format(emitter_node), rate)
            cmds.setAttr("{}.speed".format(emitter_node), speed)

        # Set position
        cmds.move(pos[0], pos[1], pos[2], particle_transform, absolute=True)

        # Find nucleus node
        nucleus_nodes = cmds.ls(type="nucleus") or []
        actual_nucleus = nucleus if nucleus and cmds.objExists(nucleus) else (
            nucleus_nodes[-1] if nucleus_nodes else None
        )

        return success_result(
            "Created nParticle '{}' with emitter '{}'".format(particle_shape, emitter_node),
            prompt="Use add_field_to_nparticles to attach gravity or turbulence fields.",
            particle_shape=particle_shape,
            emitter=emitter_node,
            nucleus=actual_nucleus,
            rate=rate,
            speed=speed,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_nparticle_emitter failed")
        return error_result("Failed to create nParticle emitter", str(exc)).to_dict()


def main(**kwargs):
    return create_nparticle_emitter(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_nparticle_emitter()))
