"""Remove constraint(s) from a target object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def remove_constraint(
    target: str,
    constraint_type: Optional[str] = None,
) -> dict:
    """Remove constraint(s) from a target object.

    Args:
        target: Name of the constrained object.
        constraint_type: If specified, only removes constraints of this type
            (``"parent"``, ``"point"``, ``"orient"``, ``"scale"``, ``"aim"``).
            If None, removes all supported constraints.

    Returns:
        ActionResultModel dict with ``context.removed`` list of removed
        constraint node names.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _TYPE_MAP = {
        "parent": "parentConstraint",
        "point": "pointConstraint",
        "orient": "orientConstraint",
        "scale": "scaleConstraint",
        "aim": "aimConstraint",
    }

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(target):
            return error_result(
                "Target not found: {}".format(target),
                "'{}' does not exist in the scene".format(target),
            ).to_dict()

        if constraint_type is not None and constraint_type not in _TYPE_MAP:
            return error_result(
                "Invalid constraint type: {}".format(constraint_type),
                "constraint_type must be one of {}".format(list(_TYPE_MAP.keys())),
            ).to_dict()

        node_types = [_TYPE_MAP[constraint_type]] if constraint_type else list(_TYPE_MAP.values())

        removed = []
        for nt in node_types:
            constraints = cmds.listRelatives(target, type=nt) or []
            for c in constraints:
                cmds.delete(c)
                removed.append(c)

        return success_result(
            "Removed {} constraint(s) from '{}'".format(len(removed), target),
            target=target,
            removed=removed,
            count=len(removed),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("remove_constraint failed")
        return error_result("Failed to remove constraints from {}".format(target), str(exc)).to_dict()



def main(**kwargs):
    return remove_constraint(**kwargs)


if __name__ == "__main__":
    import json
    result = remove_constraint()
    print(json.dumps(result))
