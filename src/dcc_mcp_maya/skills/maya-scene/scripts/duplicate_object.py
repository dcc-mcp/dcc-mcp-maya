"""Duplicate an object in the Maya scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def duplicate_object(
    object_name: str,
    new_name: Optional[str] = None,
    instance: bool = False,
) -> dict:
    """Duplicate an object in the Maya scene.

    Args:
        object_name: Name of the object to duplicate.
        new_name: Optional name for the duplicated object.
        instance: If True, create an instance instead of a full copy.

    Returns:
        ActionResultModel dict with ``context.object_name`` of the new object.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        result = cmds.duplicate(object_name, instanceLeaf=instance, returnRootsOnly=True)
        new_obj = result[0]
        if new_name:
            new_obj = cmds.rename(new_obj, new_name)

        return success_result(
            "Duplicated '{}' as '{}'".format(object_name, new_obj),
            object_name=new_obj,
            source=object_name,
            instance=instance,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("duplicate_object failed")
        return error_result("Failed to duplicate '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`duplicate_object`."""
    return duplicate_object(**kwargs)


if __name__ == "__main__":
    import json

    result = duplicate_object()
    print(json.dumps(result))
