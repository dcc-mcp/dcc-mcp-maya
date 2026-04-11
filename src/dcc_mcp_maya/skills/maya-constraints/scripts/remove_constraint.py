"""Remove constraint(s) from a target object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

_CONSTRAINT_NODE_TYPES = [
    "parentConstraint",
    "pointConstraint",
    "orientConstraint",
    "scaleConstraint",
    "aimConstraint",
    "geometryConstraint",
    "normalConstraint",
    "tangentConstraint",
]


def remove_constraint(
    target: str,
    constraint_type: Optional[str] = None,
) -> dict:
    """Remove constraint(s) from a target object.

    Args:
        target: Name of the driven (target) object.
        constraint_type: If provided (e.g. ``"parentConstraint"``), only remove
            constraints of this type.  If None, remove all constraint nodes.

    Returns:
        ActionResultModel dict with ``context.removed`` — list of deleted nodes.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, target)
        if err:
            return err

        types_to_check = [constraint_type] if constraint_type else _CONSTRAINT_NODE_TYPES
        removed = []

        for ctype in types_to_check:
            nodes = cmds.listRelatives(target, type=ctype, fullPath=True) or []
            # Also search connected constraints not directly under the transform
            connected = cmds.listConnections(target, type=ctype, source=False, destination=True) or []
            nodes = list(set(nodes + connected))
            for node in nodes:
                if cmds.objExists(node):
                    cmds.delete(node)
                    removed.append(node)

        if not removed:
            msg = "No constraints found on '{}'".format(target)
        else:
            msg = "Removed {} constraint(s) from '{}'".format(len(removed), target)

        return skill_success(
            msg, target=target, removed=removed, prompt="Use list_constraints to verify the constraint was removed."
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to remove constraint")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`remove_constraint`."""
    return remove_constraint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
