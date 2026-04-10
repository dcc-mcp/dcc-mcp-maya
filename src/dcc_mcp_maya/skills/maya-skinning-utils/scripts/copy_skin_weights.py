"""Copy skin weights from one mesh to another."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Copy skin weights between two meshes using surface distance sampling.

    Args:
        params: dict with keys:
            source (str): Source mesh with skinCluster (required).
            destination (str): Destination mesh to receive weights (required).
            surface_association (str): 'closestPoint' | 'rayCast' | 'closestComponent'. Default 'closestPoint'.
            influence_association (str): 'closestJoint' | 'oneToOne' | 'label'. Default 'closestJoint'.

    Returns:
        ActionResultModel with copy status.
    """
    source = params.get("source", "")
    destination = params.get("destination", "")
    surface_assoc = params.get("surface_association", "closestPoint")
    influence_assoc = params.get("influence_association", "closestJoint")

    if not source:
        return error_result("Missing parameter", "'source' is required")
    if not destination:
        return error_result("Missing parameter", "'destination' is required")

    try:
        if not cmds.objExists(source):
            return error_result(
                "Source not found", "Mesh '{}' does not exist".format(source)
            )
        if not cmds.objExists(destination):
            return error_result(
                "Destination not found", "Mesh '{}' does not exist".format(destination)
            )

        cmds.copySkinWeights(
            sourceSkin=source,
            destinationSkin=destination,
            noMirror=True,
            surfaceAssociation=surface_assoc,
            influenceAssociation=influence_assoc,
        )

        return success_result(
            "Copied skin weights from '{}' to '{}'".format(source, destination),
            prompt="Use normalize_skin_weights to ensure all weights sum to 1.0.",
            source=source,
            destination=destination,
            surface_association=surface_assoc,
            influence_association=influence_assoc,
        )
    except Exception as exc:
        return error_result("Failed to copy skin weights", str(exc))
