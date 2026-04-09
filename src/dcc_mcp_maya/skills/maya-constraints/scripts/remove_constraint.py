"""Remove constraint(s) from a target object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(target):
            return error_result(
                "Object not found: {}".format(target),
                "'{}' does not exist".format(target),
            ).to_dict()

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

        return success_result(
            msg,
            target=target,
            removed=removed,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_constraint failed")
        return error_result("Failed to remove constraint", str(exc)).to_dict()


def main(**kwargs):
    return remove_constraint(**kwargs)


if __name__ == "__main__":
    import json

    result = remove_constraint("pCube1")
    print(json.dumps(result))
