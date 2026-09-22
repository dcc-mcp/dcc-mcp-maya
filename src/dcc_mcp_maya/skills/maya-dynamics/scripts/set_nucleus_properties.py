"""Edit global Nucleus solver settings."""

from __future__ import annotations

from typing import Any, Dict, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import NUCLEUS_ATTRS, NucleusContractError
from dcc_mcp_maya.nucleus import set_nucleus_properties as _set_nucleus_properties

_PROPERTY_KEYS = tuple(sorted(NUCLEUS_ATTRS))


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def set_nucleus_properties(
    solver: Optional[str] = None,
    **properties: Any,
) -> dict:
    """Edit gravity, wind, substeps, scale and other solver settings."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        requested = _collect_properties(properties)
        if not requested:
            return maya_error(
                "No properties supplied",
                "set_nucleus_properties needs at least one setting to edit.",
                possible_solutions=["Pass e.g. gravity=9.8, substeps=6, space_scale=0.01."],
            )

        result = _set_nucleus_properties(cmds, solver=solver, properties=requested)
        return maya_success(
            "Updated Nucleus solver: {}".format(result["nucleus"]),
            nucleus=result["nucleus"],
            properties=result["properties"],
            prompt="Re-run the simulation, then create_ncache once the result is approved.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid Nucleus solver request",
            str(exc),
            possible_solutions=[
                "Supported settings: " + ", ".join(sorted(NUCLEUS_ATTRS)),
                "Omit solver to edit the first Nucleus node, or create one with create_nucleus.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to edit Nucleus solver")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_nucleus_properties`."""
    return set_nucleus_properties(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
