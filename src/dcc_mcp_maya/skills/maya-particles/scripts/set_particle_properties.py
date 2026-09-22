"""Edit look and physics attributes on Maya particle shapes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.particles import NPARTICLE_ATTRS, ParticleContractError
from dcc_mcp_maya.particles import set_particle_properties as _set_particle_properties

_PROPERTY_KEYS = tuple(sorted(NPARTICLE_ATTRS))


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def set_particle_properties(
    particles: Optional[List[str]] = None,
    **properties: Any,
) -> dict:
    """Edit lifespan, render type, radius, colour and collision attributes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = particles or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No particles selected",
                "Provide particles or select one or more particle shapes.",
                possible_solutions=["Pass particles=['nParticleShape1'] or select the shape before editing."],
            )

        requested = _collect_properties(properties)
        if not requested:
            return maya_error(
                "No properties supplied",
                "set_particle_properties needs at least one attribute to edit.",
                possible_solutions=["Pass e.g. particle_render_type='spheres', radius=0.05, lifespan=2.0."],
            )

        result = _set_particle_properties(cmds, targets, requested)
        return maya_success(
            "Updated {} particle shape(s)".format(result["count"]),
            updated=result["updated"],
            count=result["count"],
            prompt="For collisions add maya-dynamics create_nrigid colliders, then cache with create_ncache.",
        )
    except ParticleContractError as exc:
        return maya_error(
            "Invalid particle property request",
            str(exc),
            possible_solutions=[
                "Supported keys: " + ", ".join(sorted(NPARTICLE_ATTRS)),
                "particle_render_type accepts points, multiPoint, numeric, spheres, sprites, streak, blobby, cloud or tube.",
                "Use list_particles to enumerate particle systems in the scene.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to edit particle properties")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_particle_properties`."""
    return set_particle_properties(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
