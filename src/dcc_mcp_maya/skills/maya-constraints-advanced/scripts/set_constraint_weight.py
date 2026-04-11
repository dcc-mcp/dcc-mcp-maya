"""Set the weight of a specific driver on a constraint."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_constraint_weight(
    constraint_node: str,
    driver_index: int,
    weight: float,
) -> dict:
    """Set the blend weight for a specific driver on a Maya constraint.

    Used to implement space-switching: set one driver to 1.0 and others to 0.0
    to blend between parent spaces.  Can be keyed for animated space switches.

    Args:
        constraint_node: Name of the constraint node.
        driver_index: Zero-based index of the driver (target) whose weight to set.
        weight: New weight value (``0.0`` to ``1.0``).

    Returns:
        ActionResultModel dict with ``context.constraint_node``,
        ``context.driver_index``, ``context.weight``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(constraint_node):
            return error_result(
                "Constraint not found: {}".format(constraint_node),
                "'{}' does not exist in the scene".format(constraint_node),
            ).to_dict()

        # Discover the weight attribute for the given index
        all_ud = cmds.listAttr(constraint_node, userDefined=True) or []
        weight_suffix = "W{}".format(driver_index)
        matching = [a for a in all_ud if a.endswith(weight_suffix)]
        if not matching:
            return error_result(
                "No weight attribute found for driver index {} on '{}'".format(driver_index, constraint_node),
                "Use get_constraint_weights to list available driver indices.",
            ).to_dict()

        w_attr = "{}.{}".format(constraint_node, matching[0])
        cmds.setAttr(w_attr, weight)

        return success_result(
            "Set weight of driver {} to {} on '{}'".format(driver_index, weight, constraint_node),
            prompt="Key this attribute on the timeline for an animated space switch.",
            constraint_node=constraint_node,
            driver_index=driver_index,
            weight=weight,
            weight_attribute=w_attr,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_constraint_weight failed")
        return error_result("Failed to set constraint weight", str(exc)).to_dict()


def main(**kwargs):
    return set_constraint_weight(**kwargs)


if __name__ == "__main__":
    import json

    result = set_constraint_weight("parentConstraint1", driver_index=0, weight=1.0)
    print(json.dumps(result))
