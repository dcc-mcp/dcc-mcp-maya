"""Add a pole vector constraint to an IK handle."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for obj in (pole_object, ik_handle):
            if not cmds.objExists(obj):
                return maya_error(
                    "Object not found: {}".format(obj),
                    "'{}' does not exist in the scene".format(obj),
                )

        ik_type = cmds.objectType(ik_handle)
        if ik_type != "ikHandle":
            return maya_error(
                "Not an IK handle: {}".format(ik_handle),
                "Expected 'ikHandle', got '{}'".format(ik_type),
            )

        result = cmds.poleVectorConstraint(pole_object, ik_handle, weight=weight)
        constraint_node = result[0] if result else ""

        return maya_success(
            "Added pole vector constraint '{}' → '{}'".format(pole_object, ik_handle),
            prompt="Use set_constraint_weight to adjust blending, or bake_constraint to key the result.",
            constraint_node=constraint_node,
            pole_object=pole_object,
            ik_handle=ik_handle,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add pole vector constraint")


def main(**kwargs):
    return add_pole_vector_constraint(**kwargs)


if __name__ == "__main__":
    import json

    result = add_pole_vector_constraint("poleVectorLocator1", "ikHandle1")
    print(json.dumps(result))
