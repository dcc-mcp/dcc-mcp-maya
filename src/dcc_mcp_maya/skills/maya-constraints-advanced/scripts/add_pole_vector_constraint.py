"""Add a pole vector constraint to an IK handle."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def add_pole_vector_constraint(
    pole_object: str,
    ik_handle: str,
    weight: float = 1.0,
) -> dict:
    """Add a pole vector constraint from a pole object to an IK handle.

    The pole vector constraint controls the rotational plane of an IK joint
    chain, typically used to direct a knee or elbow towards a control object.

    Args:
        pole_object: Name of the pole vector control object (usually a locator).
        ik_handle: Name of the IK handle node.
        weight: Constraint weight.  Default ``1.0``.

    Returns:
        ActionResultModel dict with ``context.constraint_node``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for obj in (pole_object, ik_handle):
            if not cmds.objExists(obj):
                return error_result(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist in the scene".format(obj),
                ).to_dict()

        ik_type = cmds.objectType(ik_handle)
        if ik_type != "ikHandle":
            return error_result(
                "Not an IK handle: {}".format(ik_handle),
                "Expected 'ikHandle', got '{}'".format(ik_type),
            ).to_dict()

        result = cmds.poleVectorConstraint(pole_object, ik_handle, weight=weight)
        constraint_node = result[0] if result else ""

        return success_result(
            "Added pole vector constraint '{}' → '{}'".format(pole_object, ik_handle),
            prompt="Use set_constraint_weight to adjust blending, or bake_constraint to key the result.",
            constraint_node=constraint_node,
            pole_object=pole_object,
            ik_handle=ik_handle,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("add_pole_vector_constraint failed")
        return error_result("Failed to add pole vector constraint", str(exc)).to_dict()


def main(**kwargs):
    return add_pole_vector_constraint(**kwargs)


if __name__ == "__main__":
    import json

    result = add_pole_vector_constraint("poleVectorLocator1", "ikHandle1")
    print(json.dumps(result))
