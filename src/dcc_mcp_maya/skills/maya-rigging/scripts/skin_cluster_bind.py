"""Bind a mesh to a set of joints using a skin cluster."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import batch_validate_nodes, maya_error, maya_from_exception, maya_success, validate_node_exists


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not joints:
            return maya_error(
                "No joints specified",
                "joints list must contain at least one joint name",
            )

        err = validate_node_exists(cmds, mesh)
        if err:
            return err

        err = batch_validate_nodes(cmds, joints)
        if err:
            return err

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

        return maya_success(
            "Bound '{}' to {} joint(s) via skin cluster '{}'".format(mesh, len(joints), sc_name),
            skin_cluster_name=sc_name,
            mesh=mesh,
            joint_count=len(joints),
            joints=joints,
            max_influences=max_influences,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to bind skin cluster on {}".format(mesh))


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`skin_cluster_bind`."""
    return skin_cluster_bind(**kwargs)


if __name__ == "__main__":
    import json

    result = skin_cluster_bind()
    print(json.dumps(result))
