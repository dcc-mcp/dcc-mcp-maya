"""List all constraints applied to a target object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

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
        ActionResultModel dict with ``context.constraints`` — list of dicts
        with ``node``, ``type``, and ``sources``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(target):
            return error_result(
                "Object not found: {}".format(target),
                "'{}' does not exist".format(target),
            ).to_dict()

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

        return success_result(
            "Found {} constraint(s) on '{}'".format(len(constraints), target),
            prompt="Use remove_constraint to delete constraints or add_constraint to add new ones.",
            target=target,
            constraints=constraints,
            count=len(constraints),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_constraints failed")
        return error_result("Failed to list constraints on '{}'".format(target), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_constraints`."""
    return list_constraints(**kwargs)


if __name__ == "__main__":
    import json

    result = list_constraints("pCube1")
    print(json.dumps(result))
