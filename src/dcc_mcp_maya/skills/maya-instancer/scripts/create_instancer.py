"""Create a particle instancer linking a particle system to instance geometry."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def create_instancer(
    particle_system: str,
    instance_objects: List[str],
    name: Optional[str] = None,
    rotation_type: int = 0,
    level_of_detail: int = 0,
) -> dict:
    """Create a Maya particle instancer node.

    Attaches *instance_objects* to a particle system so each particle renders
    as a copy of one of the provided geometry objects.

    Args:
        particle_system: Name of the nParticle or legacy particle transform node.
        instance_objects: List of geometry transform nodes to use as instance shapes.
        name: Optional name for the instancer node.
        rotation_type: Particle rotation type: ``0`` = None, ``1`` = Initial State,
            ``2`` = Velocity * Speed, ``3`` = Velocity, ``4`` = Age.
        level_of_detail: ``0`` = Geometry, ``1`` = Bounding Box, ``2`` = Bounding Box / Faces.

    Returns:
        ActionResultModel dict with ``context.instancer_node`` and
        ``context.instance_objects``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(particle_system):
            return maya_error(
                "Particle system not found: {}".format(particle_system),
                "'{}' does not exist".format(particle_system),
            )

        missing = [o for o in instance_objects if not cmds.objExists(o)]
        if missing:
            return maya_error(
                "Instance objects not found",
                "Missing: {}".format(", ".join(missing)),
            )

        kwargs = {
            "object": instance_objects,
            "rotationType": rotation_type,
            "levelOfDetail": level_of_detail,
        }
        if name:
            kwargs["name"] = name

        node = cmds.particleInstancer(particle_system, **kwargs)

        return maya_success(
            "Created instancer '{}' with {} object(s)".format(node, len(instance_objects)),
            prompt=(
                "Use add_instance_object to add more geometry, "
                "or set_instancer_attribute to configure per-particle attributes."
            ),
            instancer_node=node,
            particle_system=particle_system,
            instance_objects=instance_objects,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create instancer")


def main(**kwargs):
    return create_instancer(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_instancer("nParticle1", ["pSphere1"]), indent=2))
