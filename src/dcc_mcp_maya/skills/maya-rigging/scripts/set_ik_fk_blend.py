"""Set the IK/FK blend weight on an IK handle."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

# Import built-in modules


def set_ik_fk_blend(
    ik_handle: str,
    blend: float = 1.0,
    attribute: str = "ikBlend",
) -> dict:
    """Set the IK/FK blend weight on an IK handle.

    Most IK solvers expose an ``ikBlend`` attribute (0 = full FK,
    1 = full IK).  This action sets that blend value and optionally
    creates a keyframe on it.

    Args:
        ik_handle: Name of the IK handle node.
        blend: Blend value between 0.0 (FK) and 1.0 (IK).  Default: 1.0.
        attribute: Name of the blend attribute on the IK handle.
            Default: ``"ikBlend"``.

    Returns:
        ActionResultModel dict with ``context.ik_handle``,
        ``context.attribute``, ``context.blend``.
    """

    if not (0.0 <= blend <= 1.0):
        return skill_error(
            "blend must be in the range [0.0, 1.0]",
            "Got blend={}".format(blend),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, ik_handle)
        if err:
            return err

        node_type = cmds.objectType(ik_handle)
        if node_type not in ("ikHandle", "transform"):
            return skill_error(
                "Not an IK handle: {}".format(ik_handle),
                "'{}' is of type '{}'; expected 'ikHandle'".format(ik_handle, node_type),
            )

        plug = "{}.{}".format(ik_handle, attribute)
        err = validate_node_exists(cmds, plug)
        if err:
            return skill_error(
                "Attribute not found: {}".format(plug),
                "IK handle '{}' does not have attribute '{}'".format(ik_handle, attribute),
            )

        cmds.setAttr(plug, blend)

        return skill_success(
            "Set IK/FK blend on '{}' to {}".format(ik_handle, blend),
            ik_handle=ik_handle,
            attribute=attribute,
            blend=blend,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set IK/FK blend on '{}'".format(ik_handle))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_ik_fk_blend`."""
    return set_ik_fk_blend(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
