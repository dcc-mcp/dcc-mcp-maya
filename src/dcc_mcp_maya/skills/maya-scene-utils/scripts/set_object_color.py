"""Set the wireframe color of a Maya object by index."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def set_object_color(
    object_name: str,
    color_index: int,
    use_default: bool = False,
) -> dict:
    """Set the wireframe color of a Maya object by index.

    Maya's viewport wireframe colour can be overridden per-object using a
    colour index (0 = default/yellow, 1–31 = custom palette entries).

    Args:
        object_name: Name of the transform to colour.
        color_index: Maya colour index (0–31).  Index 0 restores the
            default colour (same as ``use_default=True``).
        use_default: When True, disable the colour override and restore the
            default wireframe colour.  Default: False.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.color_index``, ``context.use_default``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not (0 <= color_index <= 31):
        return error_result(
            "Invalid color_index: {}".format(color_index),
            "color_index must be between 0 and 31",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result(
                "Object not found: {}".format(object_name),
                "'{}' does not exist in the scene".format(object_name),
            ).to_dict()

        if use_default or color_index == 0:
            cmds.setAttr("{}.overrideEnabled".format(object_name), False)
            cmds.setAttr("{}.overrideColor".format(object_name), 0)
            effective_index = 0
        else:
            cmds.setAttr("{}.overrideEnabled".format(object_name), True)
            cmds.setAttr("{}.overrideColor".format(object_name), color_index)
            effective_index = color_index

        return success_result(
            "Set wireframe color on '{}' to index {}".format(object_name, effective_index),
            object_name=object_name,
            color_index=effective_index,
            use_default=use_default,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_object_color failed")
        return error_result("Failed to set object color on '{}'".format(object_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_object_color`."""
    return set_object_color(**kwargs)


if __name__ == "__main__":
    import json

    result = set_object_color()
    print(json.dumps(result))
