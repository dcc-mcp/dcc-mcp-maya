"""Set an attribute on a Maya nRigid (passive collider) shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_success

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

def set_nrigid_attribute(
    nrigid_node,  # type: str
    attribute,  # type: str
    value,  # type: object
):
    # type: (...) -> dict
    """Set an attribute on a Maya nRigid (passive collider) shape node.

    Args:
        nrigid_node: Name of the nRigid shape node.
        attribute: Attribute name to set (e.g. ``"thickness"``, ``"bounce"``).
        value: New value. Scalar, triple-list (``[r, g, b]`` / ``[x, y, z]``),
            or string.

    Returns:
        ActionResultModel dict with ``context.nrigid_node``,
        ``context.attribute``, ``context.value``.
    """
    if not nrigid_node or not attribute:
        return maya_error(
            "nrigid_node and attribute are required",
            "Provide non-empty nrigid_node and attribute strings",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(nrigid_node):
            return maya_error(
                "nRigid node not found: {}".format(nrigid_node),
                "'{}' does not exist in the scene".format(nrigid_node),
            )

        node_type = cmds.objectType(nrigid_node)
        if node_type != "nRigid":
            return maya_error(
                "Not an nRigid node: {}".format(nrigid_node),
                "Expected node type 'nRigid', got '{}'".format(node_type),
            )

        attr_path = "{}.{}".format(nrigid_node, attribute)
        if not cmds.objExists(attr_path):
            return maya_error(
                "Attribute not found: {}".format(attr_path),
                "'{}' does not have attribute '{}'".format(nrigid_node, attribute),
            )

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(attr_path, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        else:
            cmds.setAttr(attr_path, value)

        return maya_success(
            "Set {}.{} = {}".format(nrigid_node, attribute, value),
            nrigid_node=nrigid_node,
            attribute=attribute,
            value=value,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_error(
            "Failed to set attribute '{}' on '{}'".format(attribute, nrigid_node),
            str(exc),
        )

def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_nrigid_attribute`."""
    return set_nrigid_attribute(**kwargs)

if __name__ == "__main__":
    import json

    result = set_nrigid_attribute()
    print(json.dumps(result))
