"""Create Maya emitters and connect them to particle systems."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.particles import EMITTER_ATTRS, EMITTER_TYPES, ParticleContractError
from dcc_mcp_maya.particles import create_emitter as _create_emitter

_PROPERTY_KEYS = (
    "rate",
    "speed",
    "speed_random",
    "tangent_speed",
    "normal_speed",
    "spread",
    "random_direction",
    "direction",
    "scale_rate_by_object_size",
    "need_parent_uv",
    "cycle_emission",
    "cycle_interval",
    "scale_speed_by_size",
    "use_distance",
    "min_distance",
    "max_distance",
    "inward_speed",
    "along_axis",
    "around_axis",
    "away_from_center",
    "away_from_axis",
    "volume_shape",
    "volume_offset",
    "volume_sweep",
    "section_radius",
    "die_on_emission_volume_exit",
    "random_seed",
)


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def create_emitter(
    emitter_type: str = "omni",
    targets: Optional[List[str]] = None,
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    **properties: Any,
) -> dict:
    """Create an omni / directional / surface / curve / volume emitter."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _create_emitter(
            cmds,
            emitter_type=emitter_type,
            name=name,
            position=position,
            targets=targets,
            properties=_collect_properties(properties),
        )
        return maya_success(
            "Created {} emitter: {}".format(result["emitter_type"], result["emitter"]),
            emitter=result["emitter"],
            emitter_type=result["emitter_type"],
            transform=result["transform"],
            targets=result["targets"],
            properties=result["properties"],
            prompt="Tune emission with set_emitter_properties (rate, speed, spread) and the look with set_particle_properties.",
        )
    except ParticleContractError as exc:
        return maya_error(
            "Invalid emitter request",
            str(exc),
            possible_solutions=[
                "emitter_type must be one of: " + ", ".join(EMITTER_TYPES),
                "Emitter keys: " + ", ".join(sorted(EMITTER_ATTRS)),
                "Pass targets=['nParticleShape1'] to connect the emitter immediately.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create emitter")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_emitter`."""
    return create_emitter(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
