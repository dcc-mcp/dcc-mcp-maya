"""Instance source geometry onto a Maya particle system."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.particles import CYCLE_MODES, ParticleContractError
from dcc_mcp_maya.particles import create_particle_instancer as _create_particle_instancer


def create_particle_instancer(
    particle: Optional[str] = None,
    objects: Optional[List[str]] = None,
    name: Optional[str] = None,
    cycle: str = "none",
    rotation_units: str = "Degrees",
    level_of_detail: str = "Geometry",
) -> dict:
    """Replace point rendering with instanced geometry per particle."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not particle:
            return maya_error(
                "particle is required",
                "An instancer needs the particle shape it should read from.",
                possible_solutions=["Pass particle='nParticleShape1' or the particle transform."],
            )
        sources = objects or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not sources:
            return maya_error(
                "No source objects for instancing",
                "Provide objects or select the geometry to instance.",
                possible_solutions=[
                    "Pass objects=['pSphere1', 'pCube1'] and cycle='sequential' to vary instances across sources."
                ],
            )

        result = _create_particle_instancer(
            cmds,
            particle=particle,
            objects=sources,
            name=name,
            cycle=cycle,
            rotation_units=rotation_units,
            level_of_detail=level_of_detail,
        )
        return maya_success(
            "Instanced {} object(s) onto {}".format(len(result["objects"]), result["particle"]),
            instancer=result["instancer"],
            particle=result["particle"],
            objects=result["objects"],
            cycle=result["cycle"],
            prompt=(
                "Drive per-instance rotation with an nParticle rotationPP attribute via "
                "maya-attributes set_attribute, or keep cycle='none' for a single source."
            ),
        )
    except ParticleContractError as exc:
        return maya_error(
            "Invalid instancer request",
            str(exc),
            possible_solutions=[
                "cycle must be one of: " + ", ".join(CYCLE_MODES),
                "particle must resolve to an nParticle or classic particle shape.",
                "Create the particle system first with create_particle_system.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create particle instancer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_particle_instancer`."""
    return create_particle_instancer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
