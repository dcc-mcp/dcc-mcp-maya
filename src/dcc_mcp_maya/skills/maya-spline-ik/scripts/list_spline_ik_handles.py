"""List all ikSplineSolver handles in the scene."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_spline_ik_handles() -> dict:
    """List all spline IK handles in the current scene.

    Returns:
        ActionResultModel dict with ``context.handles`` (list of dicts with
        ``name``, ``start_joint``, ``end_effector``, and ``curve`` keys)
        and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        all_handles = cmds.ls(type="ikHandle") or []
        spline_handles = [h for h in all_handles if cmds.ikHandle(h, query=True, solver=True) == "ikSplineSolver"]

        results = []
        for h in spline_handles:
            try:
                start_joint = cmds.ikHandle(h, query=True, startJoint=True)
                end_effector = cmds.ikHandle(h, query=True, endEffector=True)
                # The curve is connected via ikHandle.inCurve
                curve_nodes = cmds.listConnections("{}.inCurve".format(h), source=True, destination=False) or []
                curve = curve_nodes[0] if curve_nodes else ""
                results.append(
                    {
                        "name": h,
                        "start_joint": start_joint,
                        "end_effector": end_effector,
                        "curve": curve,
                    }
                )
            except Exception:
                results.append({"name": h, "start_joint": "", "end_effector": "", "curve": ""})

        return success_result(
            "Found {} spline IK handle(s)".format(len(results)),
            prompt="Use set_spline_ik_twist to configure twist, or add_stretch_to_spline_ik for stretch.",
            handles=results,
            count=len(results),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_spline_ik_handles failed")
        return error_result("Failed to list spline IK handles", str(exc)).to_dict()


def main(**kwargs):
    return list_spline_ik_handles(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(list_spline_ik_handles(), indent=2))
