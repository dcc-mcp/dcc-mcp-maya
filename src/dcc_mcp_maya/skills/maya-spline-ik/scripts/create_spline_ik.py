"""Create a spline IK handle between two joints."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for jnt in (start_joint, end_joint):
            if not cmds.objExists(jnt):
                return maya_error(
                    "Joint not found: {}".format(jnt),
                    "'{}' does not exist".format(jnt),
                )

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

        return maya_success(
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
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create spline IK")


def main(**kwargs):
    return create_spline_ik(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_spline_ik("spine_01", "spine_05"), indent=2))
