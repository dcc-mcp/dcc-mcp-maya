"""Set an attribute on a Maya nCloth shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ncloth_node):
            return maya_error(
                "nCloth node not found: {}".format(ncloth_node),
                "'{}' does not exist in the scene".format(ncloth_node),
            )

        node_type = cmds.objectType(ncloth_node)
        if node_type != "nCloth":
            return maya_error(
                "Not an nCloth node: {}".format(ncloth_node),
                "Expected node type 'nCloth', got '{}'".format(node_type),
            )

        plug = "{}.{}".format(ncloth_node, attribute)
        if not cmds.objExists(plug):
            return maya_error(
                "Attribute not found: {}".format(plug),
                "'{}' does not have attribute '{}'".format(ncloth_node, attribute),
            )

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(plug, value, type="string")
        else:
            cmds.setAttr(plug, value)

        return maya_success(
            "Set '{}.{}' = {}".format(ncloth_node, attribute, value),
            ncloth_node=ncloth_node,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set attribute on nCloth '{}'".format(ncloth_node))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_ncloth_attribute`."""
    return set_ncloth_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_ncloth_attribute()
    print(json.dumps(result))
