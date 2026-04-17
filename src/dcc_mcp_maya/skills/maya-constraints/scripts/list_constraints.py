"""List all constraints applied to a target object."""

# Import future modules
from __future__ import annotations

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


def list_constraints(target: str) -> dict:
    """List all constraints applied to a Maya object.

    Args:
        target: Name of the driven (target) object.

    Returns:
        ToolResult dict with ``context.constraints`` — list of dicts
        with ``node``, ``type``, and ``sources``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, target)
        if err:
            return err

        constraints = []
        seen = set()
        for ctype in _CONSTRAINT_NODE_TYPES:
            nodes = cmds.listRelatives(target, type=ctype, fullPath=False) or []
            connected = cmds.listConnections(target, type=ctype, source=False, destination=True) or []
            for node in set(nodes + connected):
                if node in seen:
                    continue
                seen.add(node)
                sources = cmds.listConnections(node, source=True, destination=False, type="transform") or []
                constraints.append(
                    {
                        "node": node,
                        "type": ctype,
                        "sources": list(set(sources) - {target}),
                    }
                )

        return skill_success(
            "Found {} constraint(s) on '{}'".format(len(constraints), target),
            prompt="Use remove_constraint to delete constraints or add_constraint to add new ones.",
            target=target,
            constraints=constraints,
            count=len(constraints),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list constraints on '{}'".format(target))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_constraints`."""
    return list_constraints(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
