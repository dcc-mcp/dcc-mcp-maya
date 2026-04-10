"""Delete a Spline IK handle (and optionally its curve)."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Delete a Spline IK handle and optionally its driving curve.

    Args:
        params: Dictionary containing:
            - ik_handle (str): Name of the spline IK handle to delete. Required.
            - delete_curve (bool): If True, also delete the connected spline curve. Default False.

    Returns:
        ActionResultModel confirming deletion.
    """
    ik_handle = params.get("ik_handle", "")
    delete_curve = bool(params.get("delete_curve", False))

    if not ik_handle:
        return error_result("Invalid parameters", "Parameter 'ik_handle' is required.")

    try:
        if not cmds.objExists(ik_handle):
            return error_result(
                "IK handle not found",
                "No node named '{}' in the scene.".format(ik_handle),
            )
        if cmds.nodeType(ik_handle) != "ikHandle":
            return error_result(
                "Invalid node type",
                "Node '{}' is not an ikHandle.".format(ik_handle),
            )

        curve_deleted = None

        if delete_curve:
            try:
                curve_list = cmds.ikHandle(ik_handle, query=True, curve=True) or []
                if curve_list:
                    curve_node = curve_list[0] if isinstance(curve_list, (list, tuple)) else curve_list
                    if cmds.objExists(str(curve_node)):
                        cmds.delete(str(curve_node))
                        curve_deleted = str(curve_node)
            except Exception:
                pass

        cmds.delete(ik_handle)

        return success_result(
            "Deleted spline IK handle '{}'".format(ik_handle),
            prompt="Use list_spline_ik_handles to verify the handle was removed.",
            deleted_ik_handle=ik_handle,
            deleted_curve=curve_deleted,
        )
    except Exception as exc:
        return error_result("Failed to delete spline IK handle", str(exc))
