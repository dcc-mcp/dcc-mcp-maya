"""Select all objects of a given Maya type."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules

def select_by_type(object_type: str) -> dict:
    """Select all objects of a given Maya type.

    Args:
        object_type: Maya node type string (e.g. ``"mesh"``, ``"transform"``,
            ``"joint"``, ``"camera"``).

    Returns:
        ActionResultModel dict with ``context.selection`` and ``context.count``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        objects = cmds.ls(type=object_type) or []
        if objects:
            cmds.select(objects, replace=True)
        else:
            cmds.select(clear=True)

        return maya_success(
            "Selected {} '{}' object(s)".format(len(objects), object_type),
            object_type=object_type,
            selection=objects,
            count=len(objects),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to select by type '{}'".format(object_type))

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`select_by_type`."""
    return select_by_type(**kwargs)

if __name__ == "__main__":
    import json

    result = select_by_type()
    print(json.dumps(result))
