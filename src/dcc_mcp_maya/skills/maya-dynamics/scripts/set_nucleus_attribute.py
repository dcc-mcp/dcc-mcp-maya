"""Set an attribute on a Maya nucleus solver node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def set_nucleus_attribute(
    nucleus: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute on a Maya nucleus solver node.

    Args:
        nucleus: Name of the nucleus node.
        attribute: Attribute name (e.g. ``"gravity"``, ``"windSpeed"``,
            ``"substeps"``, ``"maxCollisionIterations"``).
        value: Scalar value, or ``[x, y, z]`` list for triple attrs such as
            ``"windDirection"``.

    Returns:
        ActionResultModel dict with ``context.nucleus``,
        ``context.attribute``, ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(nucleus):
            return error_result(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            ).to_dict()

        node_type = cmds.objectType(nucleus)
        if node_type != "nucleus":
            return error_result(
                "Not a nucleus node: {}".format(nucleus),
                "Expected node type 'nucleus', got '{}'".format(node_type),
            ).to_dict()

        plug = "{}.{}".format(nucleus, attribute)
        if not cmds.objExists(plug):
            return error_result(
                "Attribute not found: {}".format(plug),
                "'{}' does not have attribute '{}'".format(nucleus, attribute),
            ).to_dict()

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(plug, value, type="string")
        else:
            cmds.setAttr(plug, value)

        return success_result(
            "Set '{}.{}' = {}".format(nucleus, attribute, value),
            nucleus=nucleus,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_nucleus_attribute failed")
        return error_result("Failed to set attribute on nucleus '{}'".format(nucleus), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_nucleus_attribute`."""
    return set_nucleus_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_nucleus_attribute()
    print(json.dumps(result))
