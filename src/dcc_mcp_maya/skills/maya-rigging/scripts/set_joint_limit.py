"""Set rotation limits on a joint axis."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional


def set_joint_limit(
    joint_name: str,
    axis: str,
    min_angle: Optional[float] = None,
    max_angle: Optional[float] = None,
    enable: bool = True,
) -> dict:
    """Set rotation limits on a joint axis.

    Limits constrain how far a joint can rotate on a given axis, preventing
    unrealistic poses during animation or IK solving.

    Args:
        joint_name: Name of the joint node to configure.
        axis: Rotation axis to limit – one of ``"x"``, ``"y"``, ``"z"``.
        min_angle: Minimum rotation angle in degrees.  If None, the existing
            minimum limit is left unchanged.
        max_angle: Maximum rotation angle in degrees.  If None, the existing
            maximum limit is left unchanged.
        enable: If True (default), enable the limit on the specified axis.
            Set to False to disable the limit without changing the stored angle
            values.

    Returns:
        ActionResultModel dict with ``context.joint_name``,
        ``context.axis``, ``context.min_angle``, ``context.max_angle``,
        ``context.enable``.
    """

    _VALID_AXES = ("x", "y", "z")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(joint_name):
            return maya_error(
                "Joint not found: {}".format(joint_name),
                "'{}' does not exist in the scene".format(joint_name),
            )

        node_type = cmds.objectType(joint_name)
        if node_type != "joint":
            return maya_error(
                "Not a joint: {}".format(joint_name),
                "'{}' is of type '{}', expected 'joint'".format(joint_name, node_type),
            )

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return maya_error(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            )

        axis_upper = axis_lower.upper()
        enable_attr_min = "minRot{}LimitEnable".format(axis_upper)
        enable_attr_max = "maxRot{}LimitEnable".format(axis_upper)
        min_attr = "minRot{}Limit".format(axis_upper)
        max_attr = "maxRot{}Limit".format(axis_upper)

        cmds.setAttr("{}.{}".format(joint_name, enable_attr_min), enable)
        cmds.setAttr("{}.{}".format(joint_name, enable_attr_max), enable)

        if min_angle is not None:
            cmds.setAttr("{}.{}".format(joint_name, min_attr), min_angle)
        if max_angle is not None:
            cmds.setAttr("{}.{}".format(joint_name, max_attr), max_angle)

        # Read back the actual stored values
        actual_min = cmds.getAttr("{}.{}".format(joint_name, min_attr))
        actual_max = cmds.getAttr("{}.{}".format(joint_name, max_attr))

        return maya_success(
            "Set rotation limit on '{}.{}': [{}, {}]".format(joint_name, axis_lower, actual_min, actual_max),
            joint_name=joint_name,
            axis=axis_lower,
            min_angle=actual_min,
            max_angle=actual_max,
            enable=enable,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set joint limit on {}".format(joint_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_joint_limit`."""
    return set_joint_limit(**kwargs)


if __name__ == "__main__":
    import json

    result = set_joint_limit()
    print(json.dumps(result))
