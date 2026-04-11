"""Create a polygon sphere."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_sphere(radius: float = 1.0, name: Optional[str] = None) -> dict:
    """Create a polygon sphere.

    Args:
        radius: Sphere radius. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"radius": radius, "subdivisionsAxis": 20, "subdivisionsHeight": 20}
        result = cmds.polySphere(**kwargs)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            f"Created sphere: {obj}",
            object_name=obj,
            radius=radius,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_sphere failed")
        return error_result("Failed to create sphere", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_sphere`."""
    return create_sphere(**kwargs)


if __name__ == "__main__":
    import json

    result = create_sphere()
    print(json.dumps(result))
