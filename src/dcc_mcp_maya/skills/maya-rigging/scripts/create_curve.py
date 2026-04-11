"""Create a NURBS curve from a list of control points."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_curve(
    points: Optional[List[List[float]]] = None,
    name: Optional[str] = None,
    degree: int = 3,
    periodic: bool = False,
) -> dict:
    """Create a NURBS curve from a list of control points.

    Args:
        points: List of ``[x, y, z]`` control-point positions.  A minimum of
            ``degree + 1`` points is required (e.g. 4 points for degree-3).
            Defaults to a simple line along the X axis if not provided.
        name: Optional name for the curve's transform node.
        degree: Curve degree.  Typical values: ``1`` (linear), ``3`` (cubic).
            Default: ``3``.
        periodic: If True, creates a closed (periodic) curve.  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.degree``, ``context.point_count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if points is None:
            # Default: a straight line with degree+2 CV points along X
            points = [[float(i), 0.0, 0.0] for i in range(degree + 2)]

        if len(points) < degree + 1:
            return skill_error(
                "Not enough control points",
                "Need at least {} points for degree-{} curve, got {}".format(degree + 1, degree, len(points)),
            )

        point_tuples = [(p[0], p[1], p[2]) for p in points]
        periodic_val = 2 if periodic else 0  # 0=open, 2=periodic

        kwargs = {
            "point": point_tuples,
            "degree": degree,
            "periodic": periodic_val,
        }
        if name:
            kwargs["name"] = name

        result = cmds.curve(**kwargs)

        return skill_success(
            "Created NURBS curve '{}'".format(result),
            object_name=result,
            degree=degree,
            point_count=len(points),
            periodic=periodic,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create curve")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_curve`."""
    return create_curve(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
