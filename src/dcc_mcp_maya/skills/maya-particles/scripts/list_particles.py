"""Summarise the particle systems, emitters and instancers in the scene."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.particles import list_particles as _list_particles


def list_particles(
    include_emitters: bool = True,
    include_instancers: bool = True,
) -> dict:
    """List every particle system, emitter and particle instancer."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _list_particles(
            cmds,
            include_emitters=include_emitters,
            include_instancers=include_instancers,
        )
        return maya_success(
            "Found {} particle system(s), {} emitter(s), {} instancer(s)".format(
                result["counts"]["particle_systems"],
                result["counts"]["emitters"],
                result["counts"]["instancers"],
            ),
            particle_systems=result["particle_systems"],
            emitters=result["emitters"],
            instancers=result["instancers"],
            counts=result["counts"],
            prompt="Attach an emitter with create_emitter, or instance geometry with create_particle_instancer.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to list particle systems")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_particles`."""
    return list_particles(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
