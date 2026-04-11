"""Configure advanced twist controls on a spline IK handle."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Maya worldUpType enum values
WORLD_UP_TYPES = {
    "scene": 0,
    "object": 1,
    "object_rotation": 2,
    "vector": 3,
    "normal": 4,
}


def set_spline_ik_twist(
    ik_handle: str,
    world_up_type: str = "vector",
    up_vector: Optional[List[float]] = None,
    up_vector_end: Optional[List[float]] = None,
    up_axis: str = "y",
    twist_type: str = "linear",
) -> dict:
    """Set advanced twist parameters on a spline IK handle.

    Args:
        ik_handle: Name of the ikSplineSolver handle node.
        world_up_type: One of ``"scene"``, ``"object"``, ``"object_rotation"``,
            ``"vector"`` (default), ``"normal"``.
        up_vector: World up vector for the root (e.g. ``[0, 1, 0]``).
            Defaults to ``[0, 1, 0]``.
        up_vector_end: World up vector at the tip.  Defaults to *up_vector*.
        up_axis: Local up axis on joints — ``"y"`` (default), ``"x"``, or ``"z"``.
        twist_type: Interpolation type — ``"linear"`` or ``"easeInOut"``.

    Returns:
        ActionResultModel dict with the configured twist parameters.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ik_handle):
            return skill_error(
                "IK handle not found: {}".format(ik_handle),
                "'{}' does not exist".format(ik_handle),
            )

        up_vec = up_vector if up_vector and len(up_vector) == 3 else [0.0, 1.0, 0.0]
        up_vec_end = up_vector_end if up_vector_end and len(up_vector_end) == 3 else up_vec

        wut = WORLD_UP_TYPES.get(world_up_type.lower(), 3)

        # Enable advanced twist
        cmds.setAttr("{}.dTwistControlEnable".format(ik_handle), True)
        cmds.setAttr("{}.dWorldUpType".format(ik_handle), wut)
        cmds.setAttr("{}.dWorldUpVector".format(ik_handle), *up_vec, type="double3")
        cmds.setAttr("{}.dWorldUpVectorEnd".format(ik_handle), *up_vec_end, type="double3")

        twist_type_val = 0 if twist_type.lower() == "linear" else 1
        cmds.setAttr("{}.dTwistValueType".format(ik_handle), twist_type_val)

        return skill_success(
            "Configured twist on '{}'".format(ik_handle),
            prompt="Test the twist by rotating joints or keying the twistRamp attribute.",
            ik_handle=ik_handle,
            world_up_type=world_up_type,
            up_vector=up_vec,
            up_vector_end=up_vec_end,
            twist_type=twist_type,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set spline IK twist")


@skill_entry
def main(**kwargs):
    return set_spline_ik_twist(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
