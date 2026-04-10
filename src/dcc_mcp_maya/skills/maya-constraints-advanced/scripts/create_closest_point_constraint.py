"""Constrain an object to the closest point on a surface or mesh."""
from __future__ import annotations

from typing import Dict

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Snap/constrain an object to the closest point on a target surface.

    Uses closestPointOnMesh or closestPointOnSurface node to compute position,
    then drives the object's translate via a constraint.

    Args:
        params: Dictionary containing:
            - object (str): The object to constrain/snap. Required.
            - target (str): The target mesh or NURBS surface. Required.
            - maintain_offset (bool): Keep current offset after constraining. Default False.
            - point_constraint_only (bool): Only constrain position (not orient). Default True.

    Returns:
        ActionResultModel with constraint setup details.
    """
    obj = str(params.get("object", ""))
    target = str(params.get("target", ""))
    maintain_offset = bool(params.get("maintain_offset", False))
    point_only = bool(params.get("point_constraint_only", True))

    if not obj or not target:
        return error_result(
            "Invalid parameters",
            "Both 'object' and 'target' are required.",
        )

    try:
        # Determine target type
        target_shapes = cmds.listRelatives(target, shapes=True) or []
        target_shape = target_shapes[0] if target_shapes else target
        node_type = cmds.nodeType(target_shape) if cmds.objExists(target_shape) else "unknown"

        if node_type == "mesh":
            cpo_node = cmds.createNode("closestPointOnMesh", name="closestPOM")
            cmds.connectAttr(
                "{}.worldMesh[0]".format(target_shape),
                "{}.inMesh".format(cpo_node),
            )
        else:
            # Treat as NURBS surface
            cpo_node = cmds.createNode("closestPointOnSurface", name="closestPOS")
            cmds.connectAttr(
                "{}.worldSpace[0]".format(target_shape),
                "{}.inputSurface".format(cpo_node),
            )

        # Feed object position into closest point query
        cmds.connectAttr(
            "{}.translate".format(obj),
            "{}.inPosition".format(cpo_node),
        )

        # Point-constrain to computed closest position
        kwargs: Dict[str, object] = {"maintainOffset": maintain_offset}
        loc = cmds.spaceLocator(name="{}_cpLoc".format(obj))[0]
        cmds.connectAttr("{}.position".format(cpo_node), "{}.translate".format(loc))

        con_nodes = []
        con_nodes.append(cmds.pointConstraint(loc, obj, **kwargs)[0])
        if not point_only:
            con_nodes.append(cmds.normalConstraint(target, obj, **kwargs)[0])

        return success_result(
            "Constrained '{}' to closest point on '{}'".format(obj, target),
            prompt="The object now snaps to the nearest surface point. Animate the object's translate to slide along the surface.",
            closest_point_node=cpo_node,
            helper_locator=loc,
            constraint_nodes=con_nodes,
        )
    except Exception as exc:
        return error_result("Failed to create closest-point constraint", str(exc))
