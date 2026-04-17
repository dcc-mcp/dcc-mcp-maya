"""Set the weight of a specific driver on a constraint."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
        ToolResult dict with ``context.constraint_node``,
        ``context.driver_index``, ``context.weight``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, constraint_node)
        if err:
            return err

        # Discover the weight attribute for the given index
        all_ud = cmds.listAttr(constraint_node, userDefined=True) or []
        weight_suffix = "W{}".format(driver_index)
        matching = [a for a in all_ud if a.endswith(weight_suffix)]
        if not matching:
            return skill_error(
                "No weight attribute found for driver index {} on '{}'".format(driver_index, constraint_node),
                "Use get_constraint_weights to list available driver indices.",
            )

        w_attr = "{}.{}".format(constraint_node, matching[0])
        cmds.setAttr(w_attr, weight)

        return skill_success(
            "Set weight of driver {} to {} on '{}'".format(driver_index, weight, constraint_node),
            prompt="Key this attribute on the timeline for an animated space switch.",
            constraint_node=constraint_node,
            driver_index=driver_index,
            weight=weight,
            weight_attribute=w_attr,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set constraint weight")


@skill_entry
def main(**kwargs):
    return set_constraint_weight(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
