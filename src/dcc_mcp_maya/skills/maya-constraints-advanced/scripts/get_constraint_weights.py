"""Query the weights of all drivers on a constraint."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_constraint_weights(constraint_node: str) -> dict:
    """Query the per-driver weights of a Maya constraint node.

    Returns each driver (target) and its current blend weight.  Useful for
    inspecting space-switch setups.

    Args:
        constraint_node: Name of the constraint node (e.g., ``parentConstraint1``).

    Returns:
        ActionResultModel dict with ``context.weights`` (list of dicts
        with ``driver`` and ``weight``) and ``context.constraint_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(constraint_node):
            return error_result(
                "Constraint not found: {}".format(constraint_node),
                "'{}' does not exist in the scene".format(constraint_node),
            ).to_dict()

        constraint_type = cmds.objectType(constraint_node)

        weight_attrs = cmds.listAttr(constraint_node, userDefined=True) or []
        weight_attrs = [a for a in weight_attrs if a.endswith("W0") or "W" in a]

        # Use constraint-specific weight query
        target_list = cmds.listConnections(
            constraint_node + ".target", source=True, destination=False
        ) or []

        weights = []
        for i, driver in enumerate(target_list):
            try:
                w_attr = "{}.{}W{}".format(
                    constraint_node,
                    driver.replace("|", "_").replace(":", "_"),
                    i,
                )
                if not cmds.objExists(w_attr):
                    # fallback: list all weight attributes
                    all_ud = cmds.listAttr(constraint_node, userDefined=True) or []
                    wattrs = [a for a in all_ud if a.endswith("W{}".format(i))]
                    w_attr = "{}.{}".format(constraint_node, wattrs[0]) if wattrs else None
                weight_val = cmds.getAttr(w_attr) if w_attr and cmds.objExists(w_attr) else 1.0
            except Exception:
                weight_val = 1.0
            weights.append({"driver": driver, "weight": weight_val})

        return success_result(
            "Constraint '{}' has {} driver(s)".format(constraint_node, len(weights)),
            prompt="Use set_constraint_weight to change a driver weight for space switching.",
            constraint_node=constraint_node,
            constraint_type=constraint_type,
            weights=weights,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_constraint_weights failed")
        return error_result("Failed to get constraint weights", str(exc)).to_dict()


def main(**kwargs):
    return get_constraint_weights(**kwargs)


if __name__ == "__main__":
    import json

    result = get_constraint_weights("parentConstraint1")
    print(json.dumps(result))
