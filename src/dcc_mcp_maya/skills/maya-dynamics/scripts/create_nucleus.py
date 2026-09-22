"""Create a standalone Nucleus solver node."""

from __future__ import annotations

from typing import Any, Dict, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import NUCLEUS_ATTRS, NucleusContractError
from dcc_mcp_maya.nucleus import create_nucleus_solver as _create_nucleus_solver

_PROPERTY_KEYS = (
    "gravity",
    "gravity_direction",
    "wind_speed",
    "wind_direction",
    "wind_noise",
    "air_density",
    "substeps",
    "max_collision_iterations",
    "collision_tolerance",
    "space_scale",
    "time_scale",
    "start_frame",
    "solver_method",
    "use_plane",
    "plane_wireframe",
)


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def create_nucleus(
    name: Optional[str] = None,
    **properties: Any,
) -> dict:
    """Create a Nucleus solver and optionally seed its global settings."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _create_nucleus_solver(cmds, name=name, properties=_collect_properties(properties))
        return maya_success(
            "Created Nucleus solver: {}".format(result["nucleus"]),
            nucleus=result["nucleus"],
            properties=result["properties"],
            prompt="Assign cloth / particles to this solver, then tune it with set_nucleus_properties.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid Nucleus solver request",
            str(exc),
            possible_solutions=[
                "Supported settings: " + ", ".join(sorted(NUCLEUS_ATTRS)),
                "gravity_direction and wind_direction take a 3-element [x, y, z] list.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create Nucleus solver")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_nucleus`."""
    return create_nucleus(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
