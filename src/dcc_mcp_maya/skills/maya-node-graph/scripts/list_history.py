"""List construction history nodes for a Maya object."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return maya_error(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            )

        kwargs = {
            "future": future,
            "levels": levels,
        }
        history_nodes = cmds.listHistory(object_name, **kwargs) or []

        history = [{"name": node, "type": cmds.objectType(node)} for node in history_nodes if node != object_name]

        return maya_success(
            "Found {} history node(s) for '{}'".format(len(history), object_name),
            object_name=object_name,
            history=history,
            count=len(history),
            future=future,
            prompt="Check the result with list_node_graph or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list history for {}".format(object_name))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_history`."""
    return list_history(**kwargs)


if __name__ == "__main__":
    import json

    result = list_history()
    print(json.dumps(result))
