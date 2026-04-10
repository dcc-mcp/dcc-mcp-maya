"""Add arc-length stretch to a spline IK chain so joints scale along the curve."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in ([ik_handle, curve] + joints):
            if not cmds.objExists(name):
                return error_result(
                    "Node not found: {}".format(name),
                    "'{}' does not exist".format(name),
                ).to_dict()

        if stretch_axis not in ("x", "y", "z"):
            return error_result(
                "Invalid stretch_axis: {}".format(stretch_axis),
                "Choose 'x', 'y', or 'z'.",
            ).to_dict()

        # Get shape from curve transform
        shape = cmds.listRelatives(curve, shapes=True, type="nurbsCurve")
        if not shape:
            return error_result(
                "No NURBS curve shape under '{}'".format(curve),
                "Provide the transform of a NURBS curve.",
            ).to_dict()
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

        return success_result(
            "Added stretch to {} joint(s) via '{}'".format(len(joints), ci),
            prompt="Animate the curve's CVs to see the joints stretch. "
                   "Use bake_transforms to collapse the result before export.",
            curve_info=ci,
            multiply_divide=md,
            joints_driven=joints,
            rest_length=rest_length,
            stretch_axis=stretch_axis,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_stretch_to_spline_ik failed")
        return error_result("Failed to add stretch", str(exc)).to_dict()


def main(**kwargs):
    return add_stretch_to_spline_ik(**kwargs)


if __name__ == "__main__":
    import json

    result = add_stretch_to_spline_ik(
        "ikHandle1",
        ["spine_01", "spine_02", "spine_03"],
        "curve1",
    )
    print(json.dumps(result, indent=2))
