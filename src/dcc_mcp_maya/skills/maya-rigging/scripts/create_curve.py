"""Create a NURBS curve from a list of control points."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if points is None:
            # Default: a straight line with degree+2 CV points along X
            points = [[float(i), 0.0, 0.0] for i in range(degree + 2)]

        if len(points) < degree + 1:
            return error_result(
                "Not enough control points",
                "Need at least {} points for degree-{} curve, got {}".format(degree + 1, degree, len(points)),
            ).to_dict()

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

        return success_result(
            "Created NURBS curve '{}'".format(result),
            object_name=result,
            degree=degree,
            point_count=len(points),
            periodic=periodic,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_curve failed")
        return error_result("Failed to create curve", str(exc)).to_dict()


def main(**kwargs):
    return create_curve(**kwargs)


if __name__ == "__main__":
    import json

    result = create_curve()
    print(json.dumps(result))
