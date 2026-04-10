"""Create a new nParticle system in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)

VALID_PARTICLE_TYPES = ("points", "spheres", "sprites", "streaks", "blobby")


def create_nparticle_system(
    name: Optional[str] = None,
    particle_type: str = "points",
    nucleus_name: Optional[str] = None,
) -> dict:
    """Create a new nParticle system with an associated nucleus solver.

    Args:
        name: Optional name for the nParticle object.
        particle_type: Particle render type — one of ``points``, ``spheres``,
            ``sprites``, ``streaks``, ``blobby``.
        nucleus_name: Optional name for the nucleus solver node.

    Returns:
        ActionResultModel dict with ``context.particle_node``, ``context.nucleus_node``,
        and ``context.particle_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if particle_type not in VALID_PARTICLE_TYPES:
        return error_result(
            "Invalid particle type '{}'".format(particle_type),
            "Valid types: {}".format(", ".join(VALID_PARTICLE_TYPES)),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Create nParticle system (cmds.nParticle returns [particleNode, ...])
        create_kwargs = {}
        if name:
            create_kwargs["name"] = name
        result = cmds.nParticle(**create_kwargs)
        particle_node = result[0] if isinstance(result, (list, tuple)) else result

        # Set render type index (0=points,1=spheres,5=sprites,6=streaks,7=blobby)
        type_index_map = {
            "points": 0,
            "spheres": 1,
            "sprites": 5,
            "streaks": 6,
            "blobby": 7,
        }
        cmds.setAttr(
            "{}.particleRenderType".format(particle_node),
            type_index_map[particle_type],
        )

        # Find or name the auto-created nucleus
        nuclei = cmds.ls(type="nucleus")
        nucleus_node = nuclei[-1] if nuclei else "nucleus1"
        if nucleus_name and nucleus_node:
            nucleus_node = cmds.rename(nucleus_node, nucleus_name)

        return success_result(
            "Created nParticle system '{}'".format(particle_node),
            prompt=(
                "Use set_nparticle_attribute to configure particle behavior, "
                "or emit_particles to attach an emitter."
            ),
            particle_node=particle_node,
            nucleus_node=nucleus_node,
            particle_type=particle_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_nparticle_system failed")
        return error_result("Failed to create nParticle system", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_nparticle_system(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_nparticle_system()))
