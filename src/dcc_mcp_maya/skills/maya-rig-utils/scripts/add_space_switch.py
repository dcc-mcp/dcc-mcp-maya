"""Add a space switch setup to a control using a parent constraint and enum attribute."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def add_space_switch(
    control: str,
    spaces: List[str],
    space_names: List[str],
    offset_node: str = "",
) -> dict:
    """Add a space switch constraint driven by an enum attribute.

    Creates a parentConstraint from the listed ``spaces`` to the
    ``offset_node`` (or ``control`` directly when offset_node is empty) and
    adds a ``space`` enum attribute on the control that drives the constraint
    weights via set driven keys.

    Args:
        control: Name of the control transform that owns the enum attribute.
        spaces: List of driver transform names (e.g. world_loc, hip_ctrl).
        space_names: Display names for each space matching the order of
            ``spaces``.  Length must equal ``len(spaces)``.
        offset_node: Intermediate node that receives the parentConstraint.
            Falls back to ``control`` when empty.

    Returns:
        ActionResultModel dict with ``context.constraint_node`` and
        ``context.space_attribute``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, control)
        if err:
            return err

        if len(spaces) != len(space_names):
            return skill_error(
                "Mismatched spaces/space_names lengths",
                "spaces ({}) and space_names ({}) must have the same length".format(len(spaces), len(space_names)),
            )

        missing = [s for s in spaces if not cmds.objExists(s)]
        if missing:
            return skill_error(
                "Driver nodes not found: {}".format(", ".join(missing)),
                "The following space drivers do not exist: {}".format(", ".join(missing)),
            )

        target = offset_node if (offset_node and cmds.objExists(offset_node)) else control

        constraint = cmds.parentConstraint(*spaces, target, maintainOffset=True)[0]

        enum_str = ":".join(space_names)
        if not cmds.attributeQuery("space", node=control, exists=True):
            cmds.addAttr(control, longName="space", attributeType="enum", enumName=enum_str, keyable=True)

        weight_attrs = cmds.parentConstraint(constraint, query=True, weightAliasList=True) or []

        for i, w_attr in enumerate(weight_attrs):
            for j in range(len(spaces)):
                cmds.setDrivenKeyframe(
                    "{}.{}".format(constraint, w_attr),
                    currentDriver="{}.space".format(control),
                    driverValue=j,
                    value=1.0 if i == j else 0.0,
                )

        return skill_success(
            "Added space switch on '{}' with {} spaces".format(control, len(spaces)),
            prompt="Set {}.space enum to switch between spaces at runtime.".format(control),
            control=control,
            constraint_node=constraint,
            space_attribute="{}.space".format(control),
            spaces=space_names,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add space switch on '{}'".format(control))


@skill_entry
def main(**kwargs):
    return add_space_switch(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
