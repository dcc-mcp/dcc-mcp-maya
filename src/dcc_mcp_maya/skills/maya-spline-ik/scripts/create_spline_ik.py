"""Create a spline IK handle between two joints."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_spline_ik(
    start_joint: str,
    end_joint: str,
    curve: Optional[str] = None,
    name: Optional[str] = None,
    num_spans: int = 2,
    root_on_curve: bool = True,
    parent_curve: bool = True,
    create_curve: bool = True,
) -> dict:
    """Create an ikSplineSolver handle linking *start_joint* to *end_joint*.

    Args:
        start_joint: Name of the root joint in the chain.
        end_joint: Name of the end joint (tip) in the chain.
        curve: Existing NURBS curve to use as the spline path.  If ``None``
            and *create_curve* is ``True``, Maya generates one automatically.
        name: Optional base name for the IK handle node.
        num_spans: Number of spans on the auto-generated curve (ignored when
            *curve* is provided).
        root_on_curve: Constrain the root joint to the curve start.
        parent_curve: Auto-parent the curve under the IK handle.
        create_curve: Auto-create a curve when no *curve* is given.

    Returns:
        ActionResultModel dict with ``context.ik_handle``, ``context.ik_effector``,
        and ``context.curve``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for jnt in (start_joint, end_joint):
            if not cmds.objExists(jnt):
                return error_result(
                    "Joint not found: {}".format(jnt),
                    "'{}' does not exist".format(jnt),
                ).to_dict()

        kwargs = {
            "startJoint": start_joint,
            "endEffector": end_joint,
            "solver": "ikSplineSolver",
            "rootOnCurve": root_on_curve,
            "parentCurve": parent_curve,
            "createCurve": create_curve if curve is None else False,
            "numSpans": num_spans,
        }
        if curve:
            kwargs["curve"] = curve
        if name:
            kwargs["name"] = name

        result = cmds.ikHandle(**kwargs)
        # result = [handleName, effectorName] or [handleName, effectorName, curveName]
        ik_handle = result[0]
        ik_effector = result[1]
        ik_curve = result[2] if len(result) > 2 else (curve or "")

        return success_result(
            "Created spline IK handle '{}'".format(ik_handle),
            prompt=(
                "Use set_spline_ik_twist to configure advanced twist, "
                "or add_stretch_to_spline_ik for length-preserving stretch."
            ),
            ik_handle=ik_handle,
            ik_effector=ik_effector,
            curve=ik_curve,
            start_joint=start_joint,
            end_joint=end_joint,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_spline_ik failed")
        return error_result("Failed to create spline IK", str(exc)).to_dict()


def main(**kwargs):
    return create_spline_ik(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_spline_ik("spine_01", "spine_05"), indent=2))
