"""List construction history nodes for a Maya object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_history(
    object_name: str,
    future: bool = False,
    levels: int = 0,
) -> dict:
    """List construction history nodes for a Maya object.

    Args:
        object_name: Name of the Maya node to inspect.
        future: If True, include *downstream* (future) nodes in addition to
            upstream history.  Default: False.
        levels: Maximum number of levels to traverse.  ``0`` means unlimited.
            Default: 0.

    Returns:
        ActionResultModel dict with ``context.history`` — a list of dicts
        with ``name`` and ``type`` for each history node, and
        ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        kwargs = {
            "future": future,
            "levels": levels,
        }
        history_nodes = cmds.listHistory(object_name, **kwargs) or []

        history = [{"name": node, "type": cmds.objectType(node)} for node in history_nodes if node != object_name]

        return success_result(
            "Found {} history node(s) for '{}'".format(len(history), object_name),
            object_name=object_name,
            history=history,
            count=len(history),
            future=future,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_history failed")
        return error_result("Failed to list history for {}".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return list_history(**kwargs)


if __name__ == "__main__":
    import json

    result = list_history()
    print(json.dumps(result))
