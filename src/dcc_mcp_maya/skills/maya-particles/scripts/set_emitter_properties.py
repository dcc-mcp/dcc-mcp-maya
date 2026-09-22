"""Edit attributes on existing Maya emitters."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.particles import EMITTER_ATTRS, ParticleContractError
from dcc_mcp_maya.particles import set_emitter_properties as _set_emitter_properties

_PROPERTY_KEYS = tuple(sorted(EMITTER_ATTRS))


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def set_emitter_properties(
    emitters: Optional[List[str]] = None,
    **properties: Any,
) -> dict:
    """Edit rate, speed, spread and other emitter attributes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = emitters or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No emitters selected",
                "Provide emitters or select one or more emitter nodes.",
                possible_solutions=["Pass emitters=['pointEmitter1'] or select the emitter before editing."],
            )

        requested = _collect_properties(properties)
        if not requested:
            return maya_error(
                "No properties supplied",
                "set_emitter_properties needs at least one attribute to edit.",
                possible_solutions=["Pass e.g. rate=200, speed=3.5, spread=0.4."],
            )

        result = _set_emitter_properties(cmds, targets, requested)
        return maya_success(
            "Updated {} emitter(s)".format(result["count"]),
            updated=result["updated"],
            count=result["count"],
            prompt="Check the look with set_particle_properties, then cache with maya-dynamics create_ncache.",
        )
    except ParticleContractError as exc:
        return maya_error(
            "Invalid emitter property request",
            str(exc),
            possible_solutions=[
                "Supported keys: " + ", ".join(sorted(EMITTER_ATTRS)),
                "Use list_particles to enumerate emitters in the scene.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to edit emitter properties")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_emitter_properties`."""
    return set_emitter_properties(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
