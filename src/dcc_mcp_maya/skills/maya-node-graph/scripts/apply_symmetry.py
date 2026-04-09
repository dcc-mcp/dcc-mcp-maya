"""Apply mesh symmetry to a polygon object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def apply_symmetry(
    object_name: str,
    axis: str = "x",
    world_space: bool = True,
) -> dict:
    """Apply mesh symmetry to a polygon object using ``cmds.symmetricModelling``.

    This enables Maya's interactive Symmetry tool on the specified axis so
    that subsequent edits are mirrored automatically.  To disable symmetry,
    call with ``axis="none"``.

    Args:
        object_name: Name of the polygon mesh transform to apply symmetry on.
        axis: Symmetry axis – one of ``"x"``, ``"y"``, ``"z"``, ``"none"``.
            Default: ``"x"``.
        world_space: If True, symmetry is evaluated in world space; otherwise
            object space.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.axis``, ``context.world_space``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_AXES = ("x", "y", "z", "none")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return error_result(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            ).to_dict()

        if axis_lower == "none":
            cmds.symmetricModelling(symmetry=False)
        else:
            space = "world" if world_space else "object"
            cmds.symmetricModelling(
                object_name,
                symmetry=True,
                axis=axis_lower,
                about=space,
            )

        return success_result(
            "Applied {} symmetry on '{}' ({} space)".format(
                axis_lower, object_name, "world" if world_space else "object"
            ),
            object_name=object_name,
            axis=axis_lower,
            world_space=world_space,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("apply_symmetry failed")
        return error_result("Failed to apply symmetry on {}".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return apply_symmetry(**kwargs)


if __name__ == "__main__":
    import json

    result = apply_symmetry()
    print(json.dumps(result))
