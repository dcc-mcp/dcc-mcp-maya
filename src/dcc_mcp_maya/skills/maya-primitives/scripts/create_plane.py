"""Create a polygon plane."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_plane(
    width: float = 1.0,
    height: float = 1.0,
    name: Optional[str] = None,
) -> dict:
    """Create a polygon plane.

    Args:
        width: Plane width. Default: 1.0.
        height: Plane height. Default: 1.0.
        name: Optional name for the created object.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.polyPlane(width=width, height=height, subdivisionsX=1, subdivisionsY=1)
        obj = result[0]
        if name:
            obj = cmds.rename(obj, name)
        return success_result(
            "Created plane: {}".format(obj),
            object_name=obj,
            width=width,
            height=height,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_plane failed")
        return error_result("Failed to create plane", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_plane`."""
    return create_plane(**kwargs)


if __name__ == "__main__":
    import json

    result = create_plane()
    print(json.dumps(result))
