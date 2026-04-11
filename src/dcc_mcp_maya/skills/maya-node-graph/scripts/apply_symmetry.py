"""Apply mesh symmetry to a polygon object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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

    _VALID_AXES = ("x", "y", "z", "none")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

        axis_lower = axis.lower()
        if axis_lower not in _VALID_AXES:
            return skill_error(
                "Invalid axis: {}".format(axis),
                "axis must be one of {}".format(_VALID_AXES),
            )

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

        return skill_success(
            "Applied {} symmetry on '{}' ({} space)".format(
                axis_lower, object_name, "world" if world_space else "object"
            ),
            object_name=object_name,
            axis=axis_lower,
            world_space=world_space,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to apply symmetry on {}".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`apply_symmetry`."""
    return apply_symmetry(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
