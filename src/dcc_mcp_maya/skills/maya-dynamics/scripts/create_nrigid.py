"""Turn meshes into passive Nucleus collision objects (nRigid)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import NCLOTH_ATTRS, NucleusContractError
from dcc_mcp_maya.nucleus import create_nrigid as _create_nrigid

_PROPERTY_KEYS = (
    "thickness",
    "bounce",
    "friction",
    "damp",
    "collision_layer",
    "push_out",
)


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def create_nrigid(
    objects: Optional[List[str]] = None,
    name: Optional[str] = None,
    **properties: Any,
) -> dict:
    """Create passive collision objects for Nucleus cloth and hair."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No objects selected for colliders",
                "Provide objects or select one or more meshes to use as colliders.",
                possible_solutions=["Pass objects=['pSphere1'] or select the collider meshes."],
            )

        result = _create_nrigid(
            cmds,
            objects=targets,
            name=name,
            properties=_collect_properties(properties),
        )
        return maya_success(
            "Created {} nRigid collider(s)".format(len(result["nrigid_nodes"])),
            nrigid_nodes=result["nrigid_nodes"],
            created=result["created"],
            prompt="Colliders only matter while an nCloth shares the same nucleus solver; check with list_dynamics.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid collider request",
            str(exc),
            possible_solutions=[
                "Check that every node in objects exists in the current scene.",
                "Supported collider keys: " + ", ".join(sorted(NCLOTH_ATTRS)),
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create nRigid colliders")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_nrigid`."""
    return create_nrigid(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
