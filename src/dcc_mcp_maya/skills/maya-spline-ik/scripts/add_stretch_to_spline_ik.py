"""Add arc-length stretch to a spline IK chain so joints scale along the curve."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def add_stretch_to_spline_ik(
    ik_handle: str,
    joints: List[str],
    curve: str,
    stretch_axis: str = "x",
) -> dict:
    """Wire up arc-length stretch for a spline IK chain.

    Measures the curve's arc length using a ``curveInfo`` node and drives each
    joint's stretch axis scale so the chain elongates/compresses with the curve.

    Args:
        ik_handle: Name of the spline IK handle (used only for naming).
        joints: Ordered list of joints that form the IK chain (root → tip).
            Excluding the very last end-effector joint is typical.
        curve: Name of the NURBS curve driving the IK handle.
        stretch_axis: Local scale axis to drive — ``"x"`` (default), ``"y"``,
            or ``"z"``.  Maya spline IK joints usually stretch on X.

    Returns:
        ActionResultModel dict with ``context.curve_info``,
        ``context.multiply_divide``, and ``context.joints_driven``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in [ik_handle, curve] + joints:
            err = validate_node_exists(cmds, name)
            if err:
                return err

        if stretch_axis not in ("x", "y", "z"):
            return skill_error(
                "Invalid stretch_axis: {}".format(stretch_axis),
                "Choose 'x', 'y', or 'z'.",
            )

        # Get shape from curve transform
        shape = cmds.listRelatives(curve, shapes=True, type="nurbsCurve")
        if not shape:
            return skill_error(
                "No NURBS curve shape under '{}'".format(curve),
                "Provide the transform of a NURBS curve.",
            )
        curve_shape = shape[0]

        base_name = ik_handle.replace("ikHandle", "").strip("_") or "splineIK"

        # curveInfo node to get arc length
        ci = cmds.createNode("curveInfo", name="{}_curveInfo".format(base_name))
        cmds.connectAttr("{}.worldSpace[0]".format(curve_shape), "{}.inputCurve".format(ci))

        rest_length = cmds.getAttr("{}.arcLength".format(ci))
        if rest_length <= 0:
            rest_length = 1.0

        # multiplyDivide node: output = arcLength / restLength → scale factor
        md = cmds.createNode("multiplyDivide", name="{}_stretch_MD".format(base_name))
        cmds.setAttr("{}.operation".format(md), 2)  # divide
        cmds.connectAttr("{}.arcLength".format(ci), "{}.input1X".format(md))
        cmds.setAttr("{}.input2X".format(md), rest_length)

        # Connect to each joint's stretch axis
        scale_attr = "scale{}".format(stretch_axis.upper())
        for jnt in joints:
            cmds.connectAttr("{}.outputX".format(md), "{}.{}".format(jnt, scale_attr), force=True)

        return skill_success(
            "Added stretch to {} joint(s) via '{}'".format(len(joints), ci),
            prompt="Animate the curve's CVs to see the joints stretch. "
            "Use bake_transforms to collapse the result before export.",
            curve_info=ci,
            multiply_divide=md,
            joints_driven=joints,
            rest_length=rest_length,
            stretch_axis=stretch_axis,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add stretch")


@skill_entry
def main(**kwargs):
    return add_stretch_to_spline_ik(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
