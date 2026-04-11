"""Add a pole vector constraint to an IK handle."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists


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
            err = validate_node_exists(cmds, obj)
            if err:
                return err

        ik_type = cmds.objectType(ik_handle)
        if ik_type != "ikHandle":
            return skill_error(
                "Not an IK handle: {}".format(ik_handle),
                "Expected 'ikHandle', got '{}'".format(ik_type),
            )

        result = cmds.poleVectorConstraint(pole_object, ik_handle, weight=weight)
        constraint_node = result[0] if result else ""

        return skill_success(
            "Added pole vector constraint '{}' → '{}'".format(pole_object, ik_handle),
            prompt="Use set_constraint_weight to adjust blending, or bake_constraint to key the result.",
            constraint_node=constraint_node,
            pole_object=pole_object,
            ik_handle=ik_handle,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add pole vector constraint")


@skill_entry
def main(**kwargs):
    return add_pole_vector_constraint(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
