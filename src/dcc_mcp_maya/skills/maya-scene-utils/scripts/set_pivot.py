"""Set the rotate and/or scale pivot of a Maya object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_PIVOT_TYPES = ("rotate", "scale", "both")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if pivot_type not in _VALID_PIVOT_TYPES:
            return error_result(
                "Invalid pivot_type: {}".format(pivot_type),
                "pivot_type must be one of {}".format(_VALID_PIVOT_TYPES),
            ).to_dict()

        if position is not None:
            if len(position) != 3:
                return error_result(
                    "Invalid position: {}".format(position),
                    "position must be a list of exactly 3 floats [x, y, z]",
                ).to_dict()

            px, py, pz = float(position[0]), float(position[1]), float(position[2])
            space_flag = {"worldSpace": True} if world_space else {}

            if pivot_type in ("rotate", "both"):
                cmds.xform(object_name, rotatePivot=[px, py, pz], **space_flag)
            if pivot_type in ("scale", "both"):
                cmds.xform(object_name, scalePivot=[px, py, pz], **space_flag)

        # Read back the actual pivot position
        rp = list(cmds.xform(object_name, query=True, rotatePivot=True, worldSpace=True))
        sp = list(cmds.xform(object_name, query=True, scalePivot=True, worldSpace=True))

        return success_result(
            "Set pivot on '{}' ({})".format(object_name, pivot_type),
            object_name=object_name,
            pivot_type=pivot_type,
            rotate_pivot=rp,
            scale_pivot=sp,
            world_space=world_space,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_pivot failed")
        return error_result("Failed to set pivot on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return set_pivot(**kwargs)


if __name__ == "__main__":
    import json

    result = set_pivot()
    print(json.dumps(result))
