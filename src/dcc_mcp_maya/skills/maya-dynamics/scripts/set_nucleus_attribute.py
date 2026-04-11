"""Set an attribute on a Maya nucleus solver node."""

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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(nucleus):
            return maya_error(
                "Nucleus node not found: {}".format(nucleus),
                "'{}' does not exist in the scene".format(nucleus),
            )

        node_type = cmds.objectType(nucleus)
        if node_type != "nucleus":
            return maya_error(
                "Not a nucleus node: {}".format(nucleus),
                "Expected node type 'nucleus', got '{}'".format(node_type),
            )

        plug = "{}.{}".format(nucleus, attribute)
        if not cmds.objExists(plug):
            return maya_error(
                "Attribute not found: {}".format(plug),
                "'{}' does not have attribute '{}'".format(nucleus, attribute),
            )

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(plug, value, type="string")
        else:
            cmds.setAttr(plug, value)

        return maya_success(
            "Set '{}.{}' = {}".format(nucleus, attribute, value),
            nucleus=nucleus,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set attribute on nucleus '{}'".format(nucleus))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_nucleus_attribute`."""
    return set_nucleus_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_nucleus_attribute()
    print(json.dumps(result))
