"""Create a rivet: attach a locator to a surface point on a polygon mesh."""
from __future__ import annotations

from typing import Dict, List

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: Dict[str, object]) -> object:
    """Create a rivet that attaches a locator to a mesh surface.

    The rivet uses loftedSurface + pointOnSurfaceInfo approach via two edge
    indices on the mesh. This is the standard Maya rivet technique.

    Args:
        params: Dictionary containing:
            - mesh (str): Name of the polygon mesh shape (or transform). Required.
            - edges (list[int]): Two edge indices to define the surface point. Required.
            - name (str): Optional name for the rivet locator.

    Returns:
        ActionResultModel with locator and rivet node names.
    """
    mesh = str(params.get("mesh", ""))
    edges_raw = params.get("edges", [])
    name = str(params.get("name", ""))

    if not mesh:
        return error_result("Invalid parameters", "'mesh' is required.")
    if not isinstance(edges_raw, (list, tuple)) or len(edges_raw) != 2:
        return error_result(
            "Invalid parameters",
            "'edges' must be a list of exactly 2 edge indices.",
        )

    edges: List[int] = [int(e) for e in edges_raw]

    try:
        # Resolve to shape if transform given
        shapes = cmds.listRelatives(mesh, shapes=True, type="mesh") or []
        shape = shapes[0] if shapes else mesh

        # curve from edges -> loft -> pointOnSurface
        c0 = cmds.createNode("curveFromMeshEdge", name="rivetEdge0_cfe")
        c1 = cmds.createNode("curveFromMeshEdge", name="rivetEdge1_cfe")
        cmds.setAttr("{}.edgeIndex[0]".format(c0), edges[0])
        cmds.setAttr("{}.edgeIndex[0]".format(c1), edges[1])
        cmds.connectAttr("{}.worldMesh".format(shape), "{}.inputMesh".format(c0))
        cmds.connectAttr("{}.worldMesh".format(shape), "{}.inputMesh".format(c1))

        loft = cmds.createNode("loft", name="rivet_loft")
        cmds.connectAttr("{}.outputCurve".format(c0), "{}.inputCurve[0]".format(loft))
        cmds.connectAttr("{}.outputCurve".format(c1), "{}.inputCurve[1]".format(loft))

        posi = cmds.createNode("pointOnSurfaceInfo", name="rivet_posi")
        cmds.setAttr("{}.parameterU".format(posi), 0.5)
        cmds.setAttr("{}.parameterV".format(posi), 0.5)
        cmds.connectAttr("{}.outputSurface".format(loft), "{}.inputSurface".format(posi))

        loc_name = name if name else "rivet_loc"
        loc = cmds.spaceLocator(name=loc_name)[0]

        aimcon = cmds.createNode("aimConstraint", name="rivet_aimCon", parent=loc)
        cmds.connectAttr("{}.normal".format(posi), "{}.target[0].targetTranslate".format(aimcon))
        cmds.connectAttr("{}.tangentV".format(posi), "{}.worldUpVector".format(aimcon))
        cmds.connectAttr("{}.constraintRotateX".format(aimcon), "{}.rotateX".format(loc))
        cmds.connectAttr("{}.constraintRotateY".format(aimcon), "{}.rotateY".format(loc))
        cmds.connectAttr("{}.constraintRotateZ".format(aimcon), "{}.rotateZ".format(loc))
        cmds.connectAttr("{}.position".format(posi), "{}.translate".format(loc))

        return success_result(
            "Created rivet locator '{}' on mesh '{}'".format(loc, mesh),
            prompt="Parent objects to the rivet locator to attach them to the surface.",
            locator=loc,
            loft_node=loft,
            posi_node=posi,
            edges=edges,
        )
    except Exception as exc:
        return error_result("Failed to create rivet", str(exc))
