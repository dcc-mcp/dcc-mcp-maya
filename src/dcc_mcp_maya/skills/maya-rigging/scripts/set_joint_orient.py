"""Set the joint orientation of a Maya joint node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(joint_name):
            return error_result(
                "Joint not found: {}".format(joint_name),
                "'{}' does not exist in the scene".format(joint_name),
            ).to_dict()

        node_type = cmds.objectType(joint_name)
        if node_type != "joint":
            return error_result(
                "Not a joint: {}".format(joint_name),
                "'{}' is of type '{}', expected 'joint'".format(joint_name, node_type),
            ).to_dict()

        ox, oy, oz = (orient or [0.0, 0.0, 0.0])[:3]
        cmds.setAttr("{}.jointOrientX".format(joint_name), ox)
        cmds.setAttr("{}.jointOrientY".format(joint_name), oy)
        cmds.setAttr("{}.jointOrientZ".format(joint_name), oz)

        if zero_scale_orient:
            for ax in ("X", "Y", "Z"):
                cmds.setAttr("{}.segmentScaleCompensate".format(joint_name), True)

        return success_result(
            "Set joint orient on '{}' to [{}, {}, {}]".format(joint_name, ox, oy, oz),
            object_name=joint_name,
            orient=[ox, oy, oz],
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_joint_orient failed")
        return error_result("Failed to set joint orient on {}".format(joint_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_joint_orient`."""
    return set_joint_orient(**kwargs)


if __name__ == "__main__":
    import json

    result = set_joint_orient()
    print(json.dumps(result))
