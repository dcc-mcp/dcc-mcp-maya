"""List all motionPath nodes in the scene with their connected objects and curves."""
from __future__ import annotations

from typing import Dict, List, Optional

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """List all motionPath nodes in the scene.

    Args:
        params: Dictionary (no required keys).
            - object_filter (str): Optional object name to filter results.

    Returns:
        ActionResultModel with list of motion path info dicts.
    """
    object_filter: Optional[str] = params.get("object_filter", None)  # type: ignore[assignment]

    try:
        mp_nodes: List[str] = cmds.ls(type="motionPath") or []
        results: List[Dict[str, object]] = []

        for mp in mp_nodes:
            info: Dict[str, object] = {"name": mp}

            # Find driven object via allCoordinates or translate connections
            driven_nodes = cmds.listConnections(
                "{}.allCoordinates".format(mp), destination=True, source=False
            ) or []
            info["driven_objects"] = driven_nodes

            # Find source curve
            curve_nodes = cmds.listConnections(
                mp, type="nurbsCurve", source=True, destination=False
            ) or []
            info["curve"] = curve_nodes[0] if curve_nodes else None

            # Current u-value
            try:
                info["u_value"] = cmds.getAttr("{}.uValue".format(mp))
            except Exception:
                info["u_value"] = None

            if object_filter and object_filter not in driven_nodes:
                continue

            results.append(info)

        return success_result(
            "Found {} motionPath node(s)".format(len(results)),
            prompt="Use create_path_constraint to attach more objects to curves.",
            motion_paths=results,
            count=len(results),
        )
    except Exception as exc:
        return error_result("Failed to list motion paths", str(exc))
