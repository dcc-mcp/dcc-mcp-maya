"""Create an nDynamics nucleus solver node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def create_nucleus(
    name: Optional[str] = None,
    gravity: float = -9.8,
    wind_speed: float = 0.0,
    wind_direction: Optional[List[float]] = None,
) -> dict:
    """Create an nDynamics nucleus solver node.

    Args:
        name: Optional name for the nucleus node.  Maya auto-names if
            ``None``.
        gravity: Gravity magnitude (world units/sec²).  Negative value pulls
            downward (default ``-9.8``).
        wind_speed: Wind speed magnitude.  Default: ``0.0`` (no wind).
        wind_direction: ``[x, y, z]`` normalised wind direction vector.
            Defaults to ``[0, 0, 1]`` (positive Z) when not provided.

    Returns:
        ActionResultModel dict with ``context.nucleus_node``,
        ``context.gravity``, ``context.wind_speed``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    wind_dir = wind_direction if (wind_direction and len(wind_direction) == 3) else [0.0, 0.0, 1.0]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        nucleus_kwargs = {}
        if name:
            nucleus_kwargs["name"] = name

        nucleus_node = cmds.createNode("nucleus", **nucleus_kwargs)

        # Configure gravity
        cmds.setAttr("{}.gravity".format(nucleus_node), gravity)

        # Configure wind
        cmds.setAttr("{}.windSpeed".format(nucleus_node), wind_speed)
        cmds.setAttr(
            "{}.windDirection".format(nucleus_node),
            wind_dir[0],
            wind_dir[1],
            wind_dir[2],
            type="double3",
        )

        # Connect to time node so the solver advances
        time_node = cmds.ls(type="time")[0] if cmds.ls(type="time") else "time1"
        if not cmds.isConnected("{}.outTime".format(time_node), "{}.currentTime".format(nucleus_node)):
            cmds.connectAttr("{}.outTime".format(time_node), "{}.currentTime".format(nucleus_node))

        return success_result(
            "Created nucleus solver '{}'".format(nucleus_node),
            nucleus_node=nucleus_node,
            gravity=gravity,
            wind_speed=wind_speed,
            wind_direction=wind_dir,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_nucleus failed")
        return error_result("Failed to create nucleus solver", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_nucleus`."""
    return create_nucleus(**kwargs)


if __name__ == "__main__":
    import json

    result = create_nucleus()
    print(json.dumps(result))
