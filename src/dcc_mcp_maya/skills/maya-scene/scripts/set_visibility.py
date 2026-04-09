"""Show or hide an object."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_visibility(object_name: str, visible: bool) -> dict:
    """Show or hide an object.

    Args:
        object_name: Name of the object to show/hide.
        visible: True to show, False to hide.

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

        cmds.setAttr("{}.visibility".format(object_name), 1 if visible else 0)
        state = "visible" if visible else "hidden"
        return success_result(
            "'{}' is now {}".format(object_name, state),
            object_name=object_name,
            visible=visible,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_visibility failed")
        return error_result("Failed to set visibility on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs):
    return set_visibility(**kwargs)


if __name__ == "__main__":
    import json

    result = set_visibility()
    print(json.dumps(result))
