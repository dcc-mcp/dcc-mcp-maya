"""Add a space switch setup to a control using a parent constraint and enum attribute."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(control):
            return error_result(
                "Control not found: {}".format(control),
                "'{}' does not exist in the scene".format(control),
            ).to_dict()

        if len(spaces) != len(space_names):
            return error_result(
                "Mismatched spaces/space_names lengths",
                "spaces ({}) and space_names ({}) must have the same length".format(len(spaces), len(space_names)),
            ).to_dict()

        missing = [s for s in spaces if not cmds.objExists(s)]
        if missing:
            return error_result(
                "Driver nodes not found: {}".format(", ".join(missing)),
                "The following space drivers do not exist: {}".format(", ".join(missing)),
            ).to_dict()

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

        return success_result(
            "Added space switch on '{}' with {} spaces".format(control, len(spaces)),
            prompt="Set {}.space enum to switch between spaces at runtime.".format(control),
            control=control,
            constraint_node=constraint,
            space_attribute="{}.space".format(control),
            spaces=space_names,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_space_switch failed")
        return error_result("Failed to add space switch on '{}'".format(control), str(exc)).to_dict()


def main(**kwargs):
    return add_space_switch(**kwargs)


if __name__ == "__main__":
    import json

    result = add_space_switch(
        "hand_ctrl",
        ["world_loc", "hip_ctrl"],
        ["world", "hip"],
    )
    print(json.dumps(result))
