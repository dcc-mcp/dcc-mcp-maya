"""Apply a UV projection to a polygon mesh."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

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
        ToolResult dict.
    """

    valid_types = ("planar", "cylindrical", "spherical")
    if projection_type not in valid_types:
        return skill_error(
            "Invalid projection_type: {}".format(projection_type),
            "Use one of: {}".format(", ".join(valid_types)),
        )

    valid_axes = ("x", "y", "z")
    if axis not in valid_axes:
        return skill_error(
            "Invalid axis: {}".format(axis),
            "Use one of: x, y, z",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, object_name)
        if err:
            return err

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

        return skill_success(
            "Applied {} UV projection to '{}' (axis={})".format(projection_type, object_name, axis),
            object_name=object_name,
            projection_type=projection_type,
            axis=axis,
            axis_index=axis_index,
            prompt="Check the result with list_uv_ops or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to project UVs")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`project_uvs`."""
    return project_uvs(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
