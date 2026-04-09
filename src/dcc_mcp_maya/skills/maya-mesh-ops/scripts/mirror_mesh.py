"""Mirror a polygon mesh along a world axis and merge the result."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    axis_lower = (axis or "x").lower()
    if axis_lower not in ("x", "y", "z"):
        return error_result(
            "Invalid axis: {}".format(axis),
            "axis must be one of 'x', 'y', 'z'",
        ).to_dict()

    if not object_name:
        return error_result(
            "object_name is required",
            "Provide a non-empty polygon mesh name",
        ).to_dict()

    # polyMirrorFace axis indices: 0=X, 1=Y, 2=Z
    axis_index = {"x": 0, "y": 1, "z": 2}[axis_lower]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

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

        return success_result(
            "Mirrored '{}' along {} axis at {}".format(object_name, axis_lower, cut_position),
            object_name=object_name,
            axis=axis_lower,
            cut_position=cut_position,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("mirror_mesh failed")
        return error_result("Failed to mirror mesh '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return mirror_mesh(**kwargs)


if __name__ == "__main__":
    import json

    result = mirror_mesh()
    print(json.dumps(result))
