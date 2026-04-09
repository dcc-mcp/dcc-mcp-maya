"""Get translate/rotate/scale of an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def get_transform(object_name: str) -> dict:
    """Get the translate/rotate/scale of an object.

    Args:
        object_name: Name of the object to query.

    Returns:
        ActionResultModel dict with translate, rotate, scale lists.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        translate = list(cmds.getAttr("{}.translate".format(object_name))[0])
        rotate = list(cmds.getAttr("{}.rotate".format(object_name))[0])
        scale = list(cmds.getAttr("{}.scale".format(object_name))[0])
        return success_result(
            "Transform of {}".format(object_name),
            object_name=object_name,
            translate=translate,
            rotate=rotate,
            scale=scale,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_transform failed")
        return error_result("Failed to get transform of {}".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return get_transform(**kwargs)


if __name__ == "__main__":
    import json

    result = get_transform()
    print(json.dumps(result))
