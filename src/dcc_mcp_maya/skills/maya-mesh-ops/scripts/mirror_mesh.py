"""Mirror a polygon mesh along a world axis and merge the result."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def mirror_mesh(
    object_name,  # type: str
    axis="x",  # type: str
    cut_position=0.0,  # type: float
    merge_threshold=0.001,  # type: float
    merge_border=True,  # type: bool
):
    # type: (...) -> dict
    """Mirror a polygon mesh along a world axis and merge the result.

    Uses ``cmds.polyMirrorFace`` to mirror the mesh about a world-axis cut
    plane and optionally merge border vertices.

    Args:
        object_name: Polygon mesh transform name.
        axis: World axis to mirror across — ``"x"``, ``"y"``, or ``"z"``.
            Default ``"x"``.
        cut_position: World-space position of the mirror plane along *axis*.
            Default ``0.0``.
        merge_threshold: Distance threshold for merging border vertices.
            Default ``0.001``.
        merge_border: If ``True`` (default), merge vertices on the mirror
            border after mirroring.

    Returns:
        ActionResultModel dict with ``context.object_name``, ``context.axis``,
        ``context.cut_position``.
    """
    axis_lower = (axis or "x").lower()
    if axis_lower not in ("x", "y", "z"):
        return skill_error(
            "Invalid axis: {}".format(axis),
            "axis must be one of 'x', 'y', 'z'",
        )

    if not object_name:
        return skill_error(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        )

    # polyMirrorFace axis indices: 0=X, 1=Y, 2=Z
    axis_index = {"x": 0, "y": 1, "z": 2}[axis_lower]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        cmds.polyMirrorFace(
            object_name,
            constructionHistory=False,
            axis=axis_index,
            axisDirection=1,
            cutMesh=1,
            worldSpace=True,
            axisPos=cut_position,
            mergeMode=1 if merge_border else 0,
            mergeThresholdType=1,
            mergeThreshold=merge_threshold,
        )

        return skill_success(
            "Mirrored '{}' along {} axis at {}".format(object_name, axis_lower, cut_position),
            object_name=object_name,
            axis=axis_lower,
            cut_position=cut_position,
            prompt="Use freeze_transforms in maya-xform-utils to clean up.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to mirror mesh '{}'".format(object_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`mirror_mesh`."""
    return mirror_mesh(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
