"""List all Spline IK handles in the current scene."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """List all ikHandle nodes that use the ikSplineSolver.

    Args:
        params: Empty dict (no parameters needed).

    Returns:
        ActionResultModel with a list of spline IK handle info dicts.
    """
    try:
        all_handles = cmds.ls(type="ikHandle") or []
        result: List[Dict[str, object]] = []
        for handle in all_handles:
            try:
                solver = cmds.ikHandle(handle, query=True, solver=True)
            except Exception:
                solver = ""
            if solver and "Spline" in solver:
                info: Dict[str, object] = {
                    "name": handle,
                    "solver": solver,
                }
                try:
                    info["stretch"] = bool(cmds.getAttr("{}.dStretch".format(handle)))
                    info["squash"] = bool(cmds.getAttr("{}.dSquash".format(handle)))
                except Exception:
                    info["stretch"] = False
                    info["squash"] = False
                result.append(info)
        return success_result(
            "Found {} spline IK handle(s)".format(len(result)),
            prompt="Use set_spline_ik_stretch or set_spline_ik_twist to configure them.",
            ik_handles=result,
            count=len(result),
        )
    except Exception as exc:
        return error_result("Failed to list spline IK handles", str(exc))
