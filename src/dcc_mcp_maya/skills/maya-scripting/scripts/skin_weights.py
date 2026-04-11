"""Maya skin weight manipulation actions.

Provides programmatic skin weight operations:
- ``get_skin_weights`` — query per-vertex weights for a skin cluster
- ``paint_skin_weights`` — set weights for specified vertices
- ``mirror_skin_weights`` — mirror a skin cluster across an axis
- ``copy_skin_weights`` — copy skin weights from one mesh to another
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def _find_skin_cluster(cmds, mesh):
    """Return the first skinCluster node in *mesh*'s history, or None."""
    history = cmds.listHistory(mesh) or []
    # cmds.ls with type filter is the most reliable way — avoids objectType mock issues
    skin_clusters = cmds.ls(history, type="skinCluster") or []
    return skin_clusters[0] if skin_clusters else None


def get_skin_weights(
    mesh: str,
    skin_cluster: Optional[str] = None,
    vertex_indices: Optional[List[int]] = None,
) -> dict:
    """Query skin weights for a mesh's skin cluster.

    Args:
        mesh: Name of the mesh transform or shape node.
        skin_cluster: Name of the skin cluster.  If None, the first skin
            cluster found on *mesh* is used automatically.
        vertex_indices: List of vertex indices to query.  If None, all
            vertices are returned.

    Returns:
        ActionResultModel dict with ``context.weights`` — a dict mapping
        vertex index (str) to a dict of ``{joint: weight}``.
        Also includes ``context.skin_cluster``, ``context.joint_count``,
        ``context.vertex_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist".format(mesh),
            ).to_dict()

        sc = skin_cluster or _find_skin_cluster(cmds, mesh)
        if not sc:
            return error_result(
                "No skin cluster on mesh: {}".format(mesh),
                "Bind a skin cluster first",
            ).to_dict()

        # Resolve shape
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        shape = shapes[0] if shapes else mesh

        # Get influencing joints
        joints = cmds.skinCluster(sc, query=True, influence=True) or []
        joint_count = len(joints)

        vtx_count = cmds.polyEvaluate(mesh, vertex=True)
        indices = vertex_indices if vertex_indices is not None else list(range(vtx_count))

        weights = {}
        for vi in indices:
            vtx = "{}.vtx[{}]".format(shape, vi)
            raw = cmds.skinPercent(sc, vtx, query=True, value=True) or []
            entry = {}
            for joint, w in zip(joints, raw):
                if w > 1e-6:
                    entry[joint] = round(w, 6)
            weights[str(vi)] = entry

        return success_result(
            "Got skin weights for '{}' ({} vertices, {} joints)".format(mesh, len(indices), joint_count),
            skin_cluster=sc,
            mesh=mesh,
            joint_count=joint_count,
            vertex_count=len(indices),
            weights=weights,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_skin_weights failed")
        return error_result("Failed to get skin weights for {}".format(mesh), str(exc)).to_dict()


def paint_skin_weights(
    mesh: str,
    joint: str,
    weight: float,
    vertex_indices: Optional[List[int]] = None,
    skin_cluster: Optional[str] = None,
    normalize: bool = True,
) -> dict:
    """Set skin weights for specified vertices on a joint.

    Args:
        mesh: Name of the mesh transform or shape node.
        joint: Name of the joint / influence to set weights on.
        weight: Weight value to assign (0.0 – 1.0).
        vertex_indices: Vertex indices to modify.  If None, all vertices
            receive the specified weight.
        skin_cluster: Name of the skin cluster.  Auto-detected if None.
        normalize: If True, normalise remaining influences after painting.

    Returns:
        ActionResultModel dict with ``context.modified_vertices`` count.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist".format(mesh),
            ).to_dict()

        if not cmds.objExists(joint):
            return error_result(
                "Joint not found: {}".format(joint),
                "'{}' does not exist".format(joint),
            ).to_dict()

        if not 0.0 <= weight <= 1.0:
            return error_result(
                "Invalid weight: {}".format(weight),
                "weight must be between 0.0 and 1.0",
            ).to_dict()

        sc = skin_cluster or _find_skin_cluster(cmds, mesh)
        if not sc:
            return error_result(
                "No skin cluster on mesh: {}".format(mesh),
                "Bind a skin cluster first",
            ).to_dict()

        # Resolve shape
        shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
        shape = shapes[0] if shapes else mesh

        vtx_count = cmds.polyEvaluate(mesh, vertex=True)
        indices = vertex_indices if vertex_indices is not None else list(range(vtx_count))

        for vi in indices:
            vtx = "{}.vtx[{}]".format(shape, vi)
            cmds.skinPercent(sc, vtx, transformValue=[(joint, weight)], normalize=normalize)

        return success_result(
            "Painted weight {:.4f} on '{}' for {} vertices".format(weight, joint, len(indices)),
            skin_cluster=sc,
            mesh=mesh,
            joint=joint,
            weight=weight,
            modified_vertices=len(indices),
            normalize=normalize,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("paint_skin_weights failed")
        return error_result("Failed to paint skin weights", str(exc)).to_dict()


def mirror_skin_weights(
    mesh: str,
    mirror_axis: str = "YZ",
    skin_cluster: Optional[str] = None,
    surface_association: str = "closestPoint",
    influence_association_1: str = "closestJoint",
    influence_association_2: str = "oneToOne",
) -> dict:
    """Mirror skin weights for a mesh across a world axis plane.

    Args:
        mesh: Name of the mesh transform.
        mirror_axis: Mirror plane — ``"YZ"`` (mirror X), ``"XY"`` (mirror Z),
            or ``"XZ"`` (mirror Y).  Default: ``"YZ"``.
        skin_cluster: Name of the skin cluster.  Auto-detected if None.
        surface_association: ``"closestPoint"``, ``"rayCast"``, or
            ``"closestComponent"``.  Default: ``"closestPoint"``.
        influence_association_1: Primary influence association method.
        influence_association_2: Secondary influence association method.

    Returns:
        ActionResultModel dict with ``context.skin_cluster`` and
        ``context.mirror_axis``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    _VALID_AXES = ("YZ", "XY", "XZ")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist".format(mesh),
            ).to_dict()

        if mirror_axis not in _VALID_AXES:
            return error_result(
                "Invalid mirror_axis: {}".format(mirror_axis),
                "mirror_axis must be one of {}".format(_VALID_AXES),
            ).to_dict()

        sc = skin_cluster or _find_skin_cluster(cmds, mesh)
        if not sc:
            return error_result(
                "No skin cluster on mesh: {}".format(mesh),
                "Bind a skin cluster first",
            ).to_dict()

        cmds.copySkinWeights(
            mesh,
            mirrorMode=mirror_axis,
            surfaceAssociation=surface_association,
            influenceAssociation=[influence_association_1, influence_association_2],
        )

        return success_result(
            "Mirrored skin weights on '{}' across {}".format(mesh, mirror_axis),
            skin_cluster=sc,
            mesh=mesh,
            mirror_axis=mirror_axis,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("mirror_skin_weights failed")
        return error_result("Failed to mirror skin weights on {}".format(mesh), str(exc)).to_dict()


def copy_skin_weights(
    source: str,
    target: str,
    surface_association: str = "closestPoint",
    influence_association: str = "closestJoint",
    normalize: bool = True,
) -> dict:
    """Copy skin weights from one mesh to another.

    Uses Maya's ``copySkinWeights`` command to transfer the skin weight data
    from *source* to *target*.  Both meshes must exist; the target mesh needs
    to have a skin cluster already bound (or ``copySkinWeights`` will create
    one automatically when possible).

    Args:
        source: Source mesh transform or shape name.
        target: Target mesh transform or shape name.
        surface_association: Method used to match surface points —
            ``"closestPoint"``, ``"rayCast"``, or ``"closestComponent"``.
            Default: ``"closestPoint"``.
        influence_association: Method used to match influences —
            ``"closestJoint"``, ``"name"``, ``"label"``, or
            ``"oneToOne"``.  Default: ``"closestJoint"``.
        normalize: If True, normalise weights after copying.  Default: True.

    Returns:
        ActionResultModel dict with ``context.source``, ``context.target``,
        ``context.surface_association`` and ``context.influence_association``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (source, target):
            if not cmds.objExists(name):
                return error_result(
                    "Object not found: {}".format(name),
                    "'{}' does not exist in the scene".format(name),
                ).to_dict()

        cmds.copySkinWeights(
            source,
            target,
            noMirror=True,
            surfaceAssociation=surface_association,
            influenceAssociation=influence_association,
            normalize=normalize,
        )

        return success_result(
            "Copied skin weights from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            surface_association=surface_association,
            influence_association=influence_association,
            normalize=normalize,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("copy_skin_weights failed")
        return error_result("Failed to copy skin weights from '{}' to '{}'".format(source, target), str(exc)).to_dict()
