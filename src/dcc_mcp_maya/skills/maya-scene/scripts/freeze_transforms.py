"""Freeze (apply) the transforms of an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def freeze_transforms(object_name: str) -> dict:
    """Freeze (apply) the transforms of an object.

    Zeroes out translate/rotate and sets scale to 1 by baking current
    transform values into the shape.

    Args:
        object_name: Name of the object whose transforms to freeze.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        cmds.makeIdentity(object_name, apply=True, translate=True, rotate=True, scale=True)
        return success_result(
            "Transforms frozen on '{}'".format(object_name),
            object_name=object_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("freeze_transforms failed")
        return error_result("Failed to freeze transforms on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return freeze_transforms(**kwargs)


if __name__ == "__main__":
    import json

    result = freeze_transforms()
    print(json.dumps(result))
