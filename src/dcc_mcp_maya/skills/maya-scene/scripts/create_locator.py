"""Create a Maya locator node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_locator(name: Optional[str] = None, position: Optional[List[float]] = None) -> dict:
    """Create a Maya locator node.

    Locators are non-renderable helper nodes commonly used as position markers,
    aim targets, or constraint targets.

    Args:
        name: Optional name for the locator's transform node.  If None, Maya
            generates a default name (``"locator1"``, etc.).
        position: Optional ``[x, y, z]`` world-space position.  If None, the
            locator is created at the origin.

    Returns:
        ActionResultModel dict with ``context.object_name`` and
        ``context.position``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        result = cmds.spaceLocator(name=name) if name else cmds.spaceLocator()
        loc_transform = result[0]

        if position and len(position) == 3:
            cmds.move(position[0], position[1], position[2], loc_transform)

        pos = position or [0.0, 0.0, 0.0]
        return success_result(
            "Created locator '{}'".format(loc_transform),
            object_name=loc_transform,
            position=pos,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_locator failed")
        return error_result("Failed to create locator", str(exc)).to_dict()


def main(**kwargs):
    return create_locator(**kwargs)


if __name__ == "__main__":
    import json

    result = create_locator()
    print(json.dumps(result))
