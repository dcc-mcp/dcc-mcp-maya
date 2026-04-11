"""Set the IK/FK blend weight on an IK handle."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not (0.0 <= blend <= 1.0):
        return error_result(
            "blend must be in the range [0.0, 1.0]",
            "Got blend={}".format(blend),
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ik_handle):
            return error_result(
                "IK handle not found: {}".format(ik_handle),
                "'{}' does not exist in the scene".format(ik_handle),
            ).to_dict()

        node_type = cmds.objectType(ik_handle)
        if node_type not in ("ikHandle", "transform"):
            return error_result(
                "Not an IK handle: {}".format(ik_handle),
                "'{}' is of type '{}'; expected 'ikHandle'".format(ik_handle, node_type),
            ).to_dict()

        plug = "{}.{}".format(ik_handle, attribute)
        if not cmds.objExists(plug):
            return error_result(
                "Attribute not found: {}".format(plug),
                "IK handle '{}' does not have attribute '{}'".format(ik_handle, attribute),
            ).to_dict()

        cmds.setAttr(plug, blend)

        return success_result(
            "Set IK/FK blend on '{}' to {}".format(ik_handle, blend),
            ik_handle=ik_handle,
            attribute=attribute,
            blend=blend,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_ik_fk_blend failed")
        return error_result("Failed to set IK/FK blend on '{}'".format(ik_handle), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`set_ik_fk_blend`."""
    return set_ik_fk_blend(**kwargs)


if __name__ == "__main__":
    import json

    result = set_ik_fk_blend()
    print(json.dumps(result))
