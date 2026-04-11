"""Set the joint orientation of a Maya joint node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import List, Optional


def set_joint_orient(
    joint_name: str,
    orient: Optional[List[float]] = None,
    zero_scale_orient: bool = False,
) -> dict:
    """Set the joint orientation of a Maya joint node.

    Joint orientation defines the local rotation axes used by the joint and
    affects how rotation channels are interpreted downstream in the rig.

    Args:
        joint_name: Name of the joint to orient.
        orient: ``[x, y, z]`` orientation in degrees.  Defaults to
            ``[0, 0, 0]`` (zero out joint orient).
        zero_scale_orient: If True, also zeroes the scale-compensate orient
            (``jointOrientX/Y/Z``).  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name`` and
        ``context.orient``.
    """

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

        ox, oy, oz = (orient or [0.0, 0.0, 0.0])[:3]
        cmds.setAttr("{}.jointOrientX".format(joint_name), ox)
        cmds.setAttr("{}.jointOrientY".format(joint_name), oy)
        cmds.setAttr("{}.jointOrientZ".format(joint_name), oz)

        if zero_scale_orient:
            for ax in ("X", "Y", "Z"):
                cmds.setAttr("{}.segmentScaleCompensate".format(joint_name), True)

        return maya_success(
            "Set joint orient on '{}' to [{}, {}, {}]".format(joint_name, ox, oy, oz),
            object_name=joint_name,
            orient=[ox, oy, oz],
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set joint orient on {}".format(joint_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_joint_orient`."""
    return set_joint_orient(**kwargs)


if __name__ == "__main__":
    import json

    result = set_joint_orient()
    print(json.dumps(result))
