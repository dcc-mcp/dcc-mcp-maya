"""Create Maya nCloth nodes from polygon meshes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import NucleusContractError
from dcc_mcp_maya.nucleus import create_ncloth as _create_ncloth

#: Tool keyword arguments that map straight onto nCloth shape attributes.
_PROPERTY_KEYS = (
    "thickness",
    "bounce",
    "friction",
    "damp",
    "mass",
    "lift",
    "drag",
    "tangential_drag",
    "stretch_resistance",
    "compression_resistance",
    "bend_resistance",
    "shear_resistance",
    "self_collide",
    "push_out",
    "input_mesh_attract",
    "collision_layer",
)


def _collect_properties(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop unset keyword arguments so only requested attributes are edited."""
    return {key: raw[key] for key in _PROPERTY_KEYS if raw.get(key) is not None}


def create_ncloth(
    objects: Optional[List[str]] = None,
    name: Optional[str] = None,
    local_space_output: bool = False,
    **properties: Any,
) -> dict:
    """Convert meshes into Nucleus nCloth objects."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No objects selected for nCloth",
                "Provide objects or select one or more polygon meshes.",
                possible_solutions=["Pass objects=['pPlane1'] or select meshes before calling create_ncloth."],
            )

        result = _create_ncloth(
            cmds,
            objects=targets,
            name=name,
            local_space_output=local_space_output,
            properties=_collect_properties(properties),
        )
        return maya_success(
            "Created {} nCloth node(s)".format(len(result["ncloth_nodes"])),
            ncloth_nodes=result["ncloth_nodes"],
            nucleus=result["nucleus"],
            created=result["created"],
            local_space_output=bool(local_space_output),
            prompt=(
                "Use create_nrigid for colliders, create_nconstraint for constraints, "
                "create_dynamic_field for forces, then create_ncache to cache the sim."
            ),
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid nCloth request",
            str(exc),
            possible_solutions=[
                "Check that every node in objects exists in the current scene.",
                "Call maya-scene list_objects to confirm the exact node names.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create nCloth")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_ncloth`."""
    return create_ncloth(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
