"""List all ikSplineSolver handles in the scene."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

# Import built-in modules


def list_spline_ik_handles() -> dict:
    """List all spline IK handles in the current scene.

    Returns:
        ActionResultModel dict with ``context.handles`` (list of dicts with
        ``name``, ``start_joint``, ``end_effector``, and ``curve`` keys)
        and ``context.count``.
    """

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

        return skill_success(
            "Found {} spline IK handle(s)".format(len(results)),
            prompt="Use set_spline_ik_twist to configure twist, or add_stretch_to_spline_ik for stretch.",
            handles=results,
            count=len(results),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list spline IK handles")


@skill_entry
def main(**kwargs):
    return list_spline_ik_handles(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
