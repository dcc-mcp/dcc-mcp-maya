"""Select all objects of a given Maya type."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def select_by_type(object_type: str) -> dict:
    """Select all objects of a given Maya type.

    Args:
        object_type: Maya node type string (e.g. ``"mesh"``, ``"transform"``,
            ``"joint"``, ``"camera"``).

    Returns:
        ActionResultModel dict with ``context.selection`` and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        objects = cmds.ls(type=object_type) or []
        if objects:
            cmds.select(objects, replace=True)
        else:
            cmds.select(clear=True)

        return success_result(
            "Selected {} '{}' object(s)".format(len(objects), object_type),
            object_type=object_type,
            selection=objects,
            count=len(objects),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("select_by_type failed")
        return error_result("Failed to select by type '{}'".format(object_type), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`select_by_type`."""
    return select_by_type(**kwargs)


if __name__ == "__main__":
    import json

    result = select_by_type()
    print(json.dumps(result))
