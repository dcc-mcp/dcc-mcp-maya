"""List objects in the current Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def list_objects(object_type: Optional[str] = None, dag: bool = True) -> dict:
    """List objects in the current Maya scene.

    Args:
        object_type: Optional Maya type filter (e.g. ``"mesh"``, ``"transform"``).
        dag: If True, only return DAG nodes.

    Returns:
        ActionResultModel dict with ``context.objects`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        kwargs = {"dag": dag}
        if object_type:
            kwargs["type"] = object_type
        objects = cmds.ls(**kwargs) or []
        return success_result(
            f"Found {len(objects)} objects",
            objects=objects,
            count=len(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_objects failed")
        return error_result("Failed to list objects", str(exc)).to_dict()


def main(**kwargs):
    return list_objects(**kwargs)


if __name__ == "__main__":
    import json

    result = list_objects()
    print(json.dumps(result))
