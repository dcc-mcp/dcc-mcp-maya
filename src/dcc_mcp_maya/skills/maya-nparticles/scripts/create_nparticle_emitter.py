"""Create an nParticle emitter attached to a nucleus solver."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415
        import maya.mel as mel  # noqa: PLC0415

        pos = position if position and len(position) == 3 else [0.0, 0.0, 0.0]

        # Create nParticle via MEL (handles nucleus wiring automatically)
        mel.eval("nParticle;")

        # Get the last created nParticle shape
        particle_shapes = cmds.ls(type="nParticle") or []
        if not particle_shapes:
            return skill_error(
                "Failed to create nParticle",
                "No nParticle node found after creation",
            )
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
            cmds.setAttr(
                "{}.emitterType".format(emitter_node), {"omni": 0, "directional": 1, "volume": 3}.get(emitter_type, 0)
            )
            cmds.setAttr("{}.rate".format(emitter_node), rate)
            cmds.setAttr("{}.speed".format(emitter_node), speed)

        # Set position
        cmds.move(pos[0], pos[1], pos[2], particle_transform, absolute=True)

        # Find nucleus node
        nucleus_nodes = cmds.ls(type="nucleus") or []
        actual_nucleus = (
            nucleus if nucleus and cmds.objExists(nucleus) else (nucleus_nodes[-1] if nucleus_nodes else None)
        )

        return skill_success(
            "Created nParticle '{}' with emitter '{}'".format(particle_shape, emitter_node),
            prompt="Use add_field_to_nparticles to attach gravity or turbulence fields.",
            particle_shape=particle_shape,
            emitter=emitter_node,
            nucleus=actual_nucleus,
            rate=rate,
            speed=speed,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create nParticle emitter")


@skill_entry
def main(**kwargs):
    return create_nparticle_emitter(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
