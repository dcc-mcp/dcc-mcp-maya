"""Create classic rigid-body constraints (nail / pin / hinge / spring / barrier)."""

from __future__ import annotations

from typing import List, Optional

from dcc_mcp_core.skill import skill_entry

from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success
from dcc_mcp_maya.nucleus import RIGID_CONSTRAINT_TYPES, NucleusContractError
from dcc_mcp_maya.nucleus import create_rigid_constraint as _create_rigid_constraint


def create_rigid_constraint(
    objects: Optional[List[str]] = None,
    constraint_type: str = "nail",
    name: Optional[str] = None,
) -> dict:
    """Constrain two or more classic rigid bodies together."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        targets = objects or [str(item) for item in (cmds.ls(selection=True) or [])]
        if not targets:
            return maya_error(
                "No rigid bodies selected",
                "Provide objects or select two or more rigid bodies.",
                possible_solutions=[
                    "Pass objects=['rigidBody1', 'rigidBody2'] or select them before calling create_rigid_constraint."
                ],
            )

        result = _create_rigid_constraint(cmds, objects=targets, constraint_type=constraint_type, name=name)
        return maya_success(
            "Created {} rigid constraint".format(result["constraint_type"]),
            constraint=result["constraint"],
            constraint_type=result["constraint_type"],
            objects=result["objects"],
            prompt="Bake the solved motion with maya-animation bake_simulation before export.",
        )
    except NucleusContractError as exc:
        return maya_error(
            "Invalid rigid constraint request",
            str(exc),
            possible_solutions=[
                "constraint_type must be one of: " + ", ".join(RIGID_CONSTRAINT_TYPES),
                "Create the rigid bodies first with make_rigid_body.",
            ],
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, message="Failed to create rigid constraint")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_rigid_constraint`."""
    return create_rigid_constraint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
