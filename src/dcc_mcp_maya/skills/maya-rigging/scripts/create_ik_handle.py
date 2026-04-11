"""Create an IK handle between two joints."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success


def create_ik_handle(
    start_joint: str,
    end_joint: str,
    solver: str = "ikRPsolver",
    name: Optional[str] = None,
) -> dict:
    """Create an IK handle between two joints.

    Args:
        start_joint: Name of the start (root) joint of the IK chain.
        end_joint: Name of the end (tip) joint of the IK chain.
        solver: IK solver to use.  Supported values:
            ``"ikRPsolver"`` (Rotate-Plane, default) or
            ``"ikSCsolver"`` (Single-Chain).
        name: Optional name for the IK handle node.  Maya auto-generates a
            name when None.

    Returns:
        ActionResultModel dict with ``context.handle_name``,
        ``context.effector_name``, and ``context.solver``.
    """

    _VALID_SOLVERS = ("ikRPsolver", "ikSCsolver")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = batch_validate_nodes(cmds, [start_joint, end_joint])
        if err:
            return err

        if solver not in _VALID_SOLVERS:
            return maya_error(
                "Invalid solver: {}".format(solver),
                "solver must be one of {}".format(_VALID_SOLVERS),
            )

        kwargs = {
            "startJoint": start_joint,
            "endEffector": end_joint,
            "solver": solver,
        }
        if name:
            kwargs["name"] = name

        result = cmds.ikHandle(**kwargs)
        handle_name = result[0]
        effector_name = result[1]

        return maya_success(
            "Created IK handle '{}'".format(handle_name),
            handle_name=handle_name,
            effector_name=effector_name,
            start_joint=start_joint,
            end_joint=end_joint,
            solver=solver,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create IK handle")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_ik_handle`."""
    return create_ik_handle(**kwargs)


if __name__ == "__main__":
    import json

    result = create_ik_handle()
    print(json.dumps(result))
