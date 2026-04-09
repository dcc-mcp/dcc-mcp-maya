"""Create a polygon cube."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_cube(
    width: float = 1.0,
    height: float = 1.0,
    depth: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon cube.

    Args:
        width: Cube width. Default: 1.0.
        height: Cube height. Default: 1.0.
        depth: Cube depth. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyCube(width=width, height=height, depth=depth)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            f"Created cube: {obj}",
            object_name=obj,
            width=width,
            height=height,
            depth=depth,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_cube failed")
        return error_result("Failed to create cube", str(exc)).to_dict()


def main(**kwargs):
    return create_cube(**kwargs)


if __name__ == "__main__":
    import json

    result = create_cube()
    print(json.dumps(result))
