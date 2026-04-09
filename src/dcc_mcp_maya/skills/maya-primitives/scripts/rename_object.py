"""Rename an object in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def rename_object(object_name: str, new_name: str) -> dict:
    """Rename a Maya object.

    Args:
        object_name: Current name of the object.
        new_name: New name to assign.

    Returns:
        ActionResultModel dict with ``context.object_name`` (new name).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        result = cmds.rename(object_name, new_name)
        return success_result(
            "Renamed '{}' to '{}'".format(object_name, result),
            old_name=object_name,
            object_name=result,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("rename_object failed")
        return error_result("Failed to rename {}".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return rename_object(**kwargs)


if __name__ == "__main__":
    import json

    result = rename_object()
    print(json.dumps(result))
