"""Create Maya nParticle or classic particle systems."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.particles import NPARTICLE_ATTRS, PARTICLE_ATTRS, ParticleContractError
from dcc_mcp_maya.particles import create_particle_system as _create_particle_system

_PROPERTY_KEYS = (
    "lifespan_mode",
    "lifespan",
    "lifespan_random",
    "particle_render_type",
    "radius",
    "conserve",
    "drag",
    "damp",
    "mass",
    "bounce",
    "friction",
    "collide",
    "self_collide",
    "opacity",
    "is_dynamic",
    "dynamics_weight",
    "level_of_detail",
    "random_seed",
)


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def create_particle_system(
    kind: str = "nparticle",
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    **properties: Any,
) -> dict:
    """Create an nParticle or classic particle system."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _create_particle_system(
            cmds,
            kind=kind,
            name=name,
            position=position,
            properties=_collect_properties(properties),
        )
        return maya_success(
            "Created {} system: {}".format(result["kind"], result["shape"]),
            kind=result["kind"],
            shape=result["shape"],
            transform=result["transform"],
            properties=result["properties"],
            prompt=(
                "Particles only emit once an emitter is attached: use create_emitter, "
                "then create_particle_instancer to instance geometry onto them."
            ),
        )
    except ParticleContractError as exc:
        return maya_error(
            "Invalid particle system request",
            str(exc),
            possible_solutions=[
                "kind must be 'nparticle' or 'classic'.",
                "nParticle keys: " + ", ".join(sorted(NPARTICLE_ATTRS)),
                "Classic particle keys: " + ", ".join(sorted(PARTICLE_ATTRS)),
                "position takes a 3-element [x, y, z] list.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create particle system")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_particle_system`."""
    return create_particle_system(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
