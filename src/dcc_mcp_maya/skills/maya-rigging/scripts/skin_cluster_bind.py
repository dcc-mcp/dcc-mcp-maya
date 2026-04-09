"""Bind a mesh to a set of joints using a skin cluster."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def skin_cluster_bind(
    joints: List[str],
    mesh: str,
    max_influences: int = 4,
    bind_method: int = 0,
    name: Optional[str] = None,
) -> dict:
    """Bind a mesh to a set of joints using a skin cluster.

    Args:
        joints: List of joint names to include in the skin cluster.
        mesh: Name of the mesh to skin.
        max_influences: Maximum number of joints that can influence each
            vertex.  Default: 4.
        bind_method: Binding algorithm:
            ``0`` = closest distance (default),
            ``1`` = closest joint,
            ``2`` = heat map,
            ``3`` = geodesic voxel.
        name: Optional name for the skin cluster node.

    Returns:
        ActionResultModel dict with ``context.skin_cluster_name``,
        ``context.joint_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not joints:
            return error_result(
                "No joints specified",
                "joints list must contain at least one joint name",
            ).to_dict()

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist in the scene".format(mesh),
            ).to_dict()

        missing = [j for j in joints if not cmds.objExists(j)]
        if missing:
            return error_result(
                "Joints not found: {}".format(", ".join(missing)),
                "The following joints do not exist: {}".format(", ".join(missing)),
            ).to_dict()

        objects = list(joints) + [mesh]
        kwargs = {
            "maximumInfluences": max_influences,
            "bindMethod": bind_method,
            "toSelectedBones": True,
        }  # type: dict
        if name:
            kwargs["name"] = name

        result = cmds.skinCluster(*objects, **kwargs)
        sc_name = result[0] if result else (name or "skinCluster1")

        return success_result(
            "Bound '{}' to {} joint(s) via skin cluster '{}'".format(mesh, len(joints), sc_name),
            skin_cluster_name=sc_name,
            mesh=mesh,
            joint_count=len(joints),
            joints=joints,
            max_influences=max_influences,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("skin_cluster_bind failed")
        return error_result("Failed to bind skin cluster on {}".format(mesh), str(exc)).to_dict()


def main(**kwargs):
    return skin_cluster_bind(**kwargs)


if __name__ == "__main__":
    import json

    result = skin_cluster_bind()
    print(json.dumps(result))
