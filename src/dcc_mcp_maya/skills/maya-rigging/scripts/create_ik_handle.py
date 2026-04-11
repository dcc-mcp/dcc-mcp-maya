"""Create an IK handle between two joints."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_SOLVERS = ("ikRPsolver", "ikSCsolver")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(start_joint):
            return error_result(
                "Start joint not found: {}".format(start_joint),
                "'{}' does not exist in the scene".format(start_joint),
            ).to_dict()

        if not cmds.objExists(end_joint):
            return error_result(
                "End joint not found: {}".format(end_joint),
                "'{}' does not exist in the scene".format(end_joint),
            ).to_dict()

        if solver not in _VALID_SOLVERS:
            return error_result(
                "Invalid solver: {}".format(solver),
                "solver must be one of {}".format(_VALID_SOLVERS),
            ).to_dict()

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

        return success_result(
            "Created IK handle '{}'".format(handle_name),
            handle_name=handle_name,
            effector_name=effector_name,
            start_joint=start_joint,
            end_joint=end_joint,
            solver=solver,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_ik_handle failed")
        return error_result("Failed to create IK handle", str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_ik_handle`."""
    return create_ik_handle(**kwargs)


if __name__ == "__main__":
    import json

    result = create_ik_handle()
    print(json.dumps(result))
