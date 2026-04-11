"""Apply a UV projection to a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

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

    valid_types = ("planar", "cylindrical", "spherical")
    if projection_type not in valid_types:
        return maya_error(
            "Invalid projection_type: {}".format(projection_type),
            "Use one of: {}".format(", ".join(valid_types)),
        )

    valid_axes = ("x", "y", "z")
    if axis not in valid_axes:
        return maya_error(
            "Invalid axis: {}".format(axis),
            "Use one of: x, y, z",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error("Object not found: {}".format(object_name))

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

        return maya_success(
            "Applied {} UV projection to '{}' (axis={})".format(projection_type, object_name, axis),
            object_name=object_name,
            projection_type=projection_type,
            axis=axis,
            axis_index=axis_index,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
                return maya_from_exception(exc, "Failed to project UVs")

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`project_uvs`."""
    return project_uvs(**kwargs)

if __name__ == "__main__":
    import json

    result = project_uvs()
    print(json.dumps(result))
