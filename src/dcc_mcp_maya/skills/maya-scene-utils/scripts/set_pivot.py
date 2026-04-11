"""Set the rotate and/or scale pivot of a Maya object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


def set_pivot(
    object_name: str,
    position: Optional[List[float]] = None,
    pivot_type: str = "both",
    world_space: bool = True,
) -> dict:
    """Set the rotate and/or scale pivot of a Maya object.

    Args:
        object_name: Name of the transform node whose pivot to set.
        position: World-space (or object-space when ``world_space=False``)
            XYZ coordinates ``[x, y, z]``.  If None, no position change is
            applied and only *pivot_type* validation is performed.
        pivot_type: Which pivot to set — ``"rotate"``, ``"scale"``, or
            ``"both"`` (default).
        world_space: If True (default), interpret *position* in world space.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.position``, ``context.pivot_type``.
    """

    _VALID_PIVOT_TYPES = ("rotate", "scale", "both")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        if pivot_type not in _VALID_PIVOT_TYPES:
            return skill_error(
                "Invalid pivot_type: {}".format(pivot_type),
                "pivot_type must be one of {}".format(_VALID_PIVOT_TYPES),
            )

        if position is not None:
            if len(position) != 3:
                return skill_error(
                    "Invalid position: {}".format(position),
                    "position must be a list of exactly 3 floats [x, y, z]",
                )

            px, py, pz = float(position[0]), float(position[1]), float(position[2])
            space_flag = {"worldSpace": True} if world_space else {}

            if pivot_type in ("rotate", "both"):
                cmds.xform(object_name, rotatePivot=[px, py, pz], **space_flag)
            if pivot_type in ("scale", "both"):
                cmds.xform(object_name, scalePivot=[px, py, pz], **space_flag)

        # Read back the actual pivot position
        rp = list(cmds.xform(object_name, query=True, rotatePivot=True, worldSpace=True))
        sp = list(cmds.xform(object_name, query=True, scalePivot=True, worldSpace=True))

        return skill_success(
            "Set pivot on '{}' ({})".format(object_name, pivot_type),
            object_name=object_name,
            pivot_type=pivot_type,
            rotate_pivot=rp,
            scale_pivot=sp,
            world_space=world_space,
            prompt="Check the result with list_scene_utils or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set pivot on '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_pivot`."""
    return set_pivot(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
