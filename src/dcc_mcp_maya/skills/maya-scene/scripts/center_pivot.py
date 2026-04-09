"""Center the pivot point of an object to its bounding box center."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def center_pivot(object_name: str) -> dict:
    """Center the pivot point of an object to its bounding box center.

    Args:
        object_name: Name of the object.

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

        cmds.xform(object_name, centerPivots=True)
        pivot = list(cmds.xform(object_name, query=True, worldSpace=True, pivots=True))
        return success_result(
            "Pivot centered on '{}'".format(object_name),
            object_name=object_name,
            pivot=pivot,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("center_pivot failed")
        return error_result("Failed to center pivot on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return center_pivot(**kwargs)


if __name__ == "__main__":
    import json

    result = center_pivot()
    print(json.dumps(result))
