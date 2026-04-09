"""List all constraints applied to a target object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def list_constraints(
    target: str,
) -> dict:
    """List all constraints applied to a target object.

    Args:
        target: Name of the constrained node to query.

    Returns:
        ActionResultModel dict with ``context.constraints`` — a list of dicts
        with ``name`` and ``type`` for each constraint found.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _CONSTRAINT_TYPES = (
        "parentConstraint",
        "pointConstraint",
        "orientConstraint",
        "scaleConstraint",
        "aimConstraint",
    )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(target):
            return error_result(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            ).to_dict()

        constraints = []
        for ct in _CONSTRAINT_TYPES:
            nodes = cmds.listRelatives(target, type=ct) or []
            for node in nodes:
                constraints.append({"name": node, "type": ct})

        return success_result(
            "Found {} constraint(s) on '{}'".format(len(constraints), target),
            target=target,
            constraints=constraints,
            count=len(constraints),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_constraints failed")
        return error_result("Failed to list constraints on {}".format(target), str(exc)).to_dict()



def main(**kwargs):
    return list_constraints(**kwargs)


if __name__ == "__main__":
    import json
    result = list_constraints()
    print(json.dumps(result))
