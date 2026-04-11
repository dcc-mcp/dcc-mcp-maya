"""Create a polygon cylinder."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_cylinder(
    radius: float = 1.0,
    height: float = 2.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon cylinder.

    Args:
        radius: Cylinder radius. Default: 1.0.
        height: Cylinder height. Default: 2.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyCylinder(radius=radius, height=height, subdivisionsAxis=20)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            f"Created cylinder: {obj}",
            object_name=obj,
            radius=radius,
            height=height,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_cylinder failed")
        return error_result("Failed to create cylinder", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_cylinder`."""
    return create_cylinder(**kwargs)


if __name__ == "__main__":
    import json

    result = create_cylinder()
    print(json.dumps(result))
