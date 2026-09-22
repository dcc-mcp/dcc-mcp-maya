"""Edit physical properties on existing Nucleus cloth and collider nodes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import NCLOTH_ATTRS, NucleusContractError, set_cloth_properties

_PROPERTY_KEYS = tuple(sorted(NCLOTH_ATTRS))


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def set_ncloth_properties(
    nodes: Optional[List[str]] = None,
    **properties: Any,
) -> dict:
    """Edit common nCloth / nRigid physical attributes."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = nodes or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No nodes selected",
                "Provide nodes or select nCloth / nRigid shapes.",
                possible_solutions=["Pass nodes=['nClothShape1'] or select the cloth before editing."],
            )

        requested = _collect_properties(properties)
        if not requested:
            return maya_error(
                "No properties supplied",
                "set_ncloth_properties needs at least one attribute to edit.",
                possible_solutions=["Pass e.g. thickness=0.05, stretch_resistance=40, damp=0.1."],
            )

        result = set_cloth_properties(cmds, targets, requested)
        return maya_success(
            "Updated {} node(s)".format(result["count"]),
            updated=result["updated"],
            count=result["count"],
            prompt="Re-run the simulation and use create_ncache once the motion is approved.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid nCloth property request",
            str(exc),
            possible_solutions=[
                "Supported keys: " + ", ".join(sorted(NCLOTH_ATTRS)),
                "Resolve the shape first with maya-node-graph describe_node.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to edit nCloth properties")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_ncloth_properties`."""
    return set_ncloth_properties(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
