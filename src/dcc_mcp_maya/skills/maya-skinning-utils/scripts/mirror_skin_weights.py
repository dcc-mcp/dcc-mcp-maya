"""Mirror skin weights across an axis on a skinCluster."""
from __future__ import annotations

import maya.cmds as cmds
from dcc_mcp_core import error_result, success_result


def run(params: dict) -> object:
    """Mirror skin weights across the YZ plane (or specified axis).

    Args:
        params: dict with keys:
            mesh (str): Mesh with skinCluster (required).
            mirror_mode (str): 'YZ' | 'XY' | 'XZ'. Default 'YZ'.
            mirror_inverse (bool): Mirror from positive to negative side. Default False.
            surface_association (str): 'closestPoint' | 'rayCast'. Default 'closestPoint'.

    Returns:
        ActionResultModel with mirror status.
    """
    mesh = params.get("mesh", "")
    mirror_mode = params.get("mirror_mode", "YZ")
    mirror_inverse = bool(params.get("mirror_inverse", False))
    surface_assoc = params.get("surface_association", "closestPoint")

    if not mesh:
        return error_result("Missing parameter", "'mesh' is required")

    valid_modes = ("YZ", "XY", "XZ")
    if mirror_mode not in valid_modes:
        return error_result(
            "Invalid mirror_mode",
            "Must be one of: {}".format(", ".join(valid_modes)),
        )

    try:
        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found", "Node '{}' does not exist".format(mesh)
            )

        cmds.copySkinWeights(
            mesh,
            mirrorMode=mirror_mode,
            mirrorInverse=mirror_inverse,
            surfaceAssociation=surface_assoc,
            influenceAssociation="closestJoint",
        )

        return success_result(
            "Mirrored skin weights on '{}' (mode={}, inverse={})".format(
                mesh, mirror_mode, mirror_inverse
            ),
            prompt="Use normalize_skin_weights to ensure weight consistency.",
            mesh=mesh,
            mirror_mode=mirror_mode,
            mirror_inverse=mirror_inverse,
        )
    except Exception as exc:
        return error_result("Failed to mirror skin weights", str(exc))
