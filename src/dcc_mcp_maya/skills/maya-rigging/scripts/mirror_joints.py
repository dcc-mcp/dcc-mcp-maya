"""Mirror a joint chain across an axis plane."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def mirror_joints(
    joint_name: str,
    mirror_behavior: bool = True,
    search_replace: Optional[List[str]] = None,
    mirror_axis: str = "YZ",
) -> dict:
    """Mirror a joint chain across an axis plane.

    Creates a mirrored copy of the joint chain starting at *joint_name*.  The
    most common use case is to build a symmetric rig (left-to-right or vice
    versa) with a single call.

    Args:
        joint_name: Root joint of the chain to mirror.
        mirror_behavior: If True, uses Maya's ``mirrorBehavior`` flag to
            invert the orientation of mirrored joints.  Default: True.
        search_replace: Two-element list ``[search, replace]`` used to rename
            mirrored joints (e.g. ``["L_", "R_"]``).  Defaults to
            ``["L_", "R_"]``.
        mirror_axis: Plane to mirror across – one of ``"YZ"``, ``"XY"``,
            ``"XZ"``.  Default: ``"YZ"``.

    Returns:
        ActionResultModel dict with ``context.mirrored_joints`` list.
    """

    _VALID_AXES = ("YZ", "XY", "XZ")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, joint_name)
        if err:
            return err

        if mirror_axis not in _VALID_AXES:
            return skill_error(
                "Invalid mirror axis: {}".format(mirror_axis),
                "mirror_axis must be one of {}".format(_VALID_AXES),
            )

        sr = search_replace or ["L_", "R_"]
        if len(sr) != 2:
            return skill_error(
                "Invalid search_replace",
                "search_replace must be a list of exactly two strings",
            )

        axis_kwargs = {
            "YZ": {"mirrorYZ": True},
            "XY": {"mirrorXY": True},
            "XZ": {"mirrorXZ": True},
        }[mirror_axis]

        mirrored = cmds.mirrorJoint(joint_name, mirrorBehavior=mirror_behavior, searchReplace=sr, **axis_kwargs)

        return skill_success(
            "Mirrored joint chain from '{}'".format(joint_name),
            source_joint=joint_name,
            mirrored_joints=list(mirrored) if mirrored else [],
            mirror_axis=mirror_axis,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to mirror joints from {}".format(joint_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`mirror_joints`."""
    return mirror_joints(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
