"""Set an attribute on a Maya nRigid (passive collider) shape node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_success

from dcc_mcp_maya.api import validate_node_exists, validate_node_type

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
        ToolResult dict with ``context.nrigid_node``,
        ``context.attribute``, ``context.value``.
    """
    if not nrigid_node or not attribute:
        return skill_error(
            "nrigid_node and attribute are required",
            "Provide non-empty nrigid_node and attribute strings",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, nrigid_node)
        if err:
            return err

        err = validate_node_type(cmds, nrigid_node, "nRigid")
        if err:
            return err

        attr_path = "{}.{}".format(nrigid_node, attribute)
        err = validate_node_exists(cmds, attr_path)
        if err:
            return skill_error(
                "Attribute not found: {}".format(attr_path),
                "'{}' does not have attribute '{}'".format(nrigid_node, attribute),
            )

        if isinstance(value, (list, tuple)) and len(value) == 3:
            cmds.setAttr(attr_path, value[0], value[1], value[2], type="double3")
        elif isinstance(value, str):
            cmds.setAttr(attr_path, value, type="string")
        else:
            cmds.setAttr(attr_path, value)

        return skill_success(
            "Set {}.{} = {}".format(nrigid_node, attribute, value),
            nrigid_node=nrigid_node,
            attribute=attribute,
            value=value,
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_error(
            "Failed to set attribute '{}' on '{}'".format(attribute, nrigid_node),
            str(exc),
        )


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_nrigid_attribute`."""
    return set_nrigid_attribute(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
