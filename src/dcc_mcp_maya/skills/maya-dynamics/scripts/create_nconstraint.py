"""Create Nucleus constraints (transform, weld, force field, ...)."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import NCONSTRAINT_TYPES, NucleusContractError
from dcc_mcp_maya.nucleus import create_nconstraint as _create_nconstraint


def create_nconstraint(
    objects: Optional[List[str]] = None,
    constraint_type: str = "transform",
    target: Optional[str] = None,
    name: Optional[str] = None,
) -> dict:
    """Constrain Nucleus cloth or particles to a driver object."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = _create_nconstraint(
            cmds,
            objects=objects,
            constraint_type=constraint_type,
            name=name,
            target=target,
        )
        return maya_success(
            "Created {} Nucleus constraint".format(result["constraint_type"]),
            constraint_type=result["constraint_type"],
            objects=result["objects"],
            target=result["target"],
            name=result["name"],
            prompt=(
                "Constraints are evaluated by the nucleus solver; adjust strength with "
                "set_ncloth_properties and tune the solver with set_nucleus_properties."
            ),
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid Nucleus constraint request",
            str(exc),
            possible_solutions=[
                "constraint_type must be one of: " + ", ".join(NCONSTRAINT_TYPES),
                "Select the driven cloth first, or pass objects=['nClothShape1'] and target='colliderMesh'.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create Nucleus constraint")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_nconstraint`."""
    return create_nconstraint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
