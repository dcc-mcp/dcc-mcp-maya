"""Apply a UV projection to a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def project_uvs(
    object_name: str,
    projection_type: str = "planar",
    axis: str = "y",
) -> dict:
    """Apply a UV projection to a polygon mesh.

    Args:
        object_name: Transform or mesh name.
        projection_type: Projection type — ``"planar"``, ``"cylindrical"``,
            or ``"spherical"``.  Default: ``"planar"``.
        axis: Projection axis — ``"x"``, ``"y"``, or ``"z"``.  Only used
            for planar and cylindrical projections.  Default: ``"y"``.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    valid_types = ("planar", "cylindrical", "spherical")
    if projection_type not in valid_types:
        return error_result(
            "Invalid projection_type: {}".format(projection_type),
            "Use one of: {}".format(", ".join(valid_types)),
        ).to_dict()

    valid_axes = ("x", "y", "z")
    if axis not in valid_axes:
        return error_result(
            "Invalid axis: {}".format(axis),
            "Use one of: x, y, z",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        axis_index = {"x": 0, "y": 1, "z": 2}[axis]

        if projection_type == "planar":
            cmds.polyProjection(
                object_name,
                type="Planar",
                mapDirection=axis.upper(),
                ch=False,
            )
        elif projection_type == "cylindrical":
            cmds.polyProjection(
                object_name,
                type="Cylindrical",
                ch=False,
            )
        else:
            cmds.polyProjection(
                object_name,
                type="Spherical",
                ch=False,
            )

        return success_result(
            "Applied {} UV projection to '{}' (axis={})".format(projection_type, object_name, axis),
            object_name=object_name,
            projection_type=projection_type,
            axis=axis,
            axis_index=axis_index,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("project_uvs failed")
        return error_result("Failed to project UVs", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`project_uvs`."""
    return project_uvs(**kwargs)


if __name__ == "__main__":
    import json

    result = project_uvs()
    print(json.dumps(result))
