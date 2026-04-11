"""Query the weights of all drivers on a constraint."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, constraint_node)
        if err:
            return err

        constraint_type = cmds.objectType(constraint_node)

        weight_attrs = cmds.listAttr(constraint_node, userDefined=True) or []
        weight_attrs = [a for a in weight_attrs if a.endswith("W0") or "W" in a]

        # Use constraint-specific weight query
        target_list = cmds.listConnections(constraint_node + ".target", source=True, destination=False) or []

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

        return skill_success(
            "Constraint '{}' has {} driver(s)".format(constraint_node, len(weights)),
            prompt="Use set_constraint_weight to change a driver weight for space switching.",
            constraint_node=constraint_node,
            constraint_type=constraint_type,
            weights=weights,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get constraint weights")


@skill_entry
def main(**kwargs):
    return get_constraint_weights(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
