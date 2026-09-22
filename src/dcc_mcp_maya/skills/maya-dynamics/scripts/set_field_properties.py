"""Edit attributes on existing Maya dynamic field nodes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import FIELD_ATTRS, NucleusContractError
from dcc_mcp_maya.nucleus import set_field_properties as _set_field_properties

_PROPERTY_KEYS = tuple(sorted(FIELD_ATTRS))


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def set_field_properties(
    fields: Optional[List[str]] = None,
    **properties: Any,
) -> dict:
    """Edit magnitude, attenuation, turbulence and other field attributes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = fields or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No fields selected",
                "Provide fields or select one or more dynamic field nodes.",
                possible_solutions=["Pass fields=['turbulenceField1'] or select the field before editing."],
            )

        requested = _collect_properties(properties)
        if not requested:
            return maya_error(
                "No properties supplied",
                "set_field_properties needs at least one attribute to edit.",
                possible_solutions=["Pass e.g. magnitude=12.0, attenuation=0.5, turbulence=2.0."],
            )

        result = _set_field_properties(cmds, targets, requested)
        return maya_success(
            "Updated {} field(s)".format(result["count"]),
            updated=result["updated"],
            count=result["count"],
            prompt="Re-run the simulation and cache it with create_ncache once the motion is approved.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid field property request",
            str(exc),
            possible_solutions=[
                "Supported keys: " + ", ".join(sorted(FIELD_ATTRS)),
                "direction and turbulence_frequency take a 3-element [x, y, z] list.",
                "Use list_dynamics to enumerate the fields present in the scene.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to edit field properties")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_field_properties`."""
    return set_field_properties(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
