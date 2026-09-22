"""Create any Maya dynamic field and optionally connect it to targets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import FIELD_COMMANDS, NucleusContractError
from dcc_mcp_maya.nucleus import create_field as _create_field

_PROPERTY_KEYS = (
    "magnitude",
    "attenuation",
    "max_distance",
    "apply_per_vertex",
    "frequency",
    "phase",
    "speed",
    "use_direction",
    "along_axis",
    "around_axis",
    "away_from_center",
    "away_from_axis",
    "directional_speed",
    "directional_strength",
    "turbulence",
    "turbulence_speed",
    "turbulence_frequency",
    "detail_turbulence",
    "section_radius",
    "trap_inside",
    "volume_shape",
    "invert_attenuation",
    "direction",
)


def _collect_settings(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested flags are passed on."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def create_dynamic_field(
    field_type: str = "air",
    targets: Optional[List[str]] = None,
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    connect: bool = True,
    **settings: Any,
) -> dict:
    """Create an air / drag / gravity / newton / radial / turbulence /
    uniform / vortex / volume-axis field."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        collected = _collect_settings(settings)
        if position is not None:
            collected["position"] = position

        result = _create_field(
            cmds,
            field_type=field_type,
            name=name,
            targets=targets,
            connect=connect,
            **collected,
        )
        return maya_success(
            "Created {} field: {}".format(result["field_type"], result["field"]),
            field=result["field"],
            field_type=result["field_type"],
            created=result["created"],
            targets=result["targets"],
            settings=result["settings"],
            prompt="Tune the field with set_field_properties once you can see its effect on the simulation.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid dynamic field request",
            str(exc),
            possible_solutions=[
                "field_type must be one of: " + ", ".join(sorted(FIELD_COMMANDS)),
                "Each field type only accepts a subset of flags; the error lists the supported ones.",
                "direction and turbulence_frequency take a 3-element [x, y, z] list.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create dynamic field")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_dynamic_field`."""
    return create_dynamic_field(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
