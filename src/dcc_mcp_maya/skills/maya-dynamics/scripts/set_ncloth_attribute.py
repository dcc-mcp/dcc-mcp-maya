"""Set an attribute on a Maya nCloth shape node."""

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


def set_ncloth_attribute(
    ncloth_node: str,
    attribute: str,
    value: object,
) -> dict:
    """Set an attribute on a Maya nCloth shape node.

    Commonly used attributes include ``"thickness"``, ``"bounce"``,
    ``"friction"``, ``"stickiness"``, ``"stretchResistance"``,
    ``"compressionResistance"``, ``"bendResistance"``, ``"damp"``,
    ``"inputMeshAttract"``, ``"lift"``, ``"drag"``.

    Args:
        ncloth_node: Name of the nCloth shape node (not the mesh transform).
        attribute: Attribute name on the nCloth node.
        value: Scalar float value, or ``[x, y, z]`` list for triple attrs.

    Returns:
        ActionResultModel dict with ``context.ncloth_node``,
        ``context.attribute``, ``context.value``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ncloth_node):
            return error_result(
                "nCloth node not found: {}".format(ncloth_node),
                "'{}' does not exist in the scene".format(ncloth_node),
            ).to_dict()

        node_type = cmds.objectType(ncloth_node)
        if node_type != "nCloth":
            return error_result(
                "Not an nCloth node: {}".format(ncloth_node),
                "Expected node type 'nCloth', got '{}'".format(node_type),
            ).to_dict()

        plug = "{}.{}".format(ncloth_node, attribute)
        if not cmds.objExists(plug):
            return error_result(
                "Attribute not found: {}".format(plug),
                "'{}' does not have attribute '{}'".format(ncloth_node, attribute),
            ).to_dict()

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(plug, value, type="string")
        else:
            cmds.setAttr(plug, value)

        return success_result(
            "Set '{}.{}' = {}".format(ncloth_node, attribute, value),
            ncloth_node=ncloth_node,
            attribute=attribute,
            value=value,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_ncloth_attribute failed")
        return error_result("Failed to set attribute on nCloth '{}'".format(ncloth_node), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_ncloth_attribute`."""
    return set_ncloth_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_ncloth_attribute()
    print(json.dumps(result))
