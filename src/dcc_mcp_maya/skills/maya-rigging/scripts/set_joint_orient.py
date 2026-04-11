"""Set the joint orientation of a Maya joint node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists, validate_node_type


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

        err = validate_node_exists(cmds, joint_name)
        if err:
            return err

        err = validate_node_type(cmds, joint_name, "joint")
        if err:
            return err

        ox, oy, oz = (orient or [0.0, 0.0, 0.0])[:3]
        cmds.setAttr("{}.jointOrientX".format(joint_name), ox)
        cmds.setAttr("{}.jointOrientY".format(joint_name), oy)
        cmds.setAttr("{}.jointOrientZ".format(joint_name), oz)

        if zero_scale_orient:
            for ax in ("X", "Y", "Z"):
                cmds.setAttr("{}.segmentScaleCompensate".format(joint_name), True)

        return skill_success(
            "Set joint orient on '{}' to [{}, {}, {}]".format(joint_name, ox, oy, oz),
            object_name=joint_name,
            orient=[ox, oy, oz],
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set joint orient on {}".format(joint_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_joint_orient`."""
    return set_joint_orient(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
