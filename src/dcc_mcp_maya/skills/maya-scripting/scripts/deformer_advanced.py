"""Advanced Maya deformer actions: cluster weights, lattice FFD, wire, sculpt."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_cluster(
    objects: List[str],
    name: Optional[str] = None,
    relative: bool = False,
) -> dict:
    """Create a cluster deformer on one or more objects.

    Args:
        objects: List of mesh names to deform.
        name: Optional name for the cluster handle.  Maya auto-names if
            ``None``.
        relative: When ``True``, the cluster operates in relative mode
            (deformation relative to the cluster handle pivot).

    Returns:
        ActionResultModel dict with ``context.cluster_node``,
        ``context.cluster_handle``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one object name in the 'objects' list",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist before creating a cluster",
            ).to_dict()

        kwargs = {"relative": relative}  # type: Dict
        if name:
            kwargs["name"] = name

        result = cmds.cluster(objects, **kwargs)
        # cmds.cluster returns [clusterNode, clusterHandle]
        cluster_node = result[0] if result else None
        cluster_handle = result[1] if result and len(result) > 1 else None

        return success_result(
            "Created cluster deformer '{}' on {} object(s)".format(cluster_node, len(objects)),
            cluster_node=cluster_node,
            cluster_handle=cluster_handle,
            objects=objects,
            relative=relative,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_cluster failed")
        return error_result("Failed to create cluster deformer", str(exc)).to_dict()


def set_cluster_weights(
    cluster_node: str,
    mesh: str,
    weights: List[float],
    vertex_indices: Optional[List[int]] = None,
    normalize: bool = True,
) -> dict:
    """Set per-vertex weights on a cluster deformer.

    Args:
        cluster_node: Name of the cluster deformer node (not the handle).
        mesh: Name of the mesh whose vertex weights to set.
        weights: Weight values, one per vertex in *vertex_indices* (or per
            all vertices if *vertex_indices* is ``None``).
        vertex_indices: Specific vertex indices to update.  If ``None``,
            *weights* must cover all vertices in order.
        normalize: When ``True``, clamp weights to ``[0, 1]`` before setting.

    Returns:
        ActionResultModel dict with ``context.vertex_count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not weights:
        return error_result(
            "No weights provided",
            "Supply at least one weight value",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(cluster_node):
            return error_result(
                "Cluster node not found: {}".format(cluster_node),
                "'{}' does not exist".format(cluster_node),
            ).to_dict()
        if not cmds.objExists(mesh):
            return error_result(
                "Mesh not found: {}".format(mesh),
                "'{}' does not exist".format(mesh),
            ).to_dict()

        vertex_count = cmds.polyEvaluate(mesh, vertex=True)

        if vertex_indices is None:
            if len(weights) != vertex_count:
                return error_result(
                    "Weight count mismatch",
                    "Expected {} weights, got {}".format(vertex_count, len(weights)),
                ).to_dict()
            vertex_indices = list(range(vertex_count))

        if normalize:
            weights = [max(0.0, min(1.0, float(w))) for w in weights]

        for idx, w in zip(vertex_indices, weights):
            vtx = "{}.vtx[{}]".format(mesh, idx)
            cmds.percent(cluster_node, vtx, value=w)

        return success_result(
            "Set cluster weights on {} vertices of '{}'".format(len(vertex_indices), mesh),
            cluster_node=cluster_node,
            mesh=mesh,
            vertex_count=len(vertex_indices),
            normalize=normalize,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_cluster_weights failed")
        return error_result("Failed to set cluster weights", str(exc)).to_dict()


def create_lattice(
    objects: List[str],
    divisions: Optional[List[int]] = None,
    name: Optional[str] = None,
    local_scale: Optional[List[float]] = None,
) -> dict:
    """Create an FFD (Free-Form Deformation) lattice on one or more objects.

    Args:
        objects: List of mesh/surface names to enclose in the lattice.
        divisions: ``[s_divisions, t_divisions, u_divisions]`` for the
            lattice control-point grid.  Defaults to ``[2, 5, 2]``.
        name: Optional base name for the lattice node.
        local_scale: Optional ``[sx, sy, sz]`` local scale applied to the
            FFD base.  If ``None``, the bounding-box size is used.

    Returns:
        ActionResultModel dict with ``context.ffd_node``,
        ``context.lattice_node``, ``context.base_node``,
        ``context.objects``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one object name in the 'objects' list",
        ).to_dict()

    divs = divisions if (divisions and len(divisions) == 3) else [2, 5, 2]

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist before creating a lattice",
            ).to_dict()

        ffd_kwargs = {
            "divisions": divs,
        }  # type: Dict
        if name:
            ffd_kwargs["name"] = name

        result = cmds.lattice(objects, **ffd_kwargs)
        # cmds.lattice returns [ffdNode, latticeShape, baseShape]
        ffd_node = result[0] if result else None
        lattice_node = result[1] if result and len(result) > 1 else None
        base_node = result[2] if result and len(result) > 2 else None

        if local_scale and lattice_node:
            cmds.setAttr("{}.sx".format(lattice_node), local_scale[0])
            cmds.setAttr("{}.sy".format(lattice_node), local_scale[1])
            cmds.setAttr("{}.sz".format(lattice_node), local_scale[2])

        return success_result(
            "Created FFD lattice '{}' ({}) on {} object(s)".format(ffd_node, divs, len(objects)),
            ffd_node=ffd_node,
            lattice_node=lattice_node,
            base_node=base_node,
            objects=objects,
            divisions=divs,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_lattice failed")
        return error_result("Failed to create FFD lattice", str(exc)).to_dict()


def wire_deformer(
    curves: List[str],
    objects: List[str],
    name: Optional[str] = None,
    dropoff_distance: float = 100.0,
) -> dict:
    """Create a wire deformer that deforms meshes along one or more NURBS curves.

    Args:
        curves: List of NURBS curve names to use as wire wires.
        objects: List of mesh/surface names to deform.
        name: Optional name for the wire deformer node.
        dropoff_distance: Distance at which the wire influence falls off to
            zero.  Default: ``100.0``.

    Returns:
        ActionResultModel dict with ``context.wire_node``,
        ``context.curves``, ``context.objects``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not curves:
        return error_result(
            "No curves specified",
            "Provide at least one NURBS curve name in 'curves'",
        ).to_dict()
    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one mesh name in 'objects'",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing_curves = [c for c in curves if not cmds.objExists(c)]
        if missing_curves:
            return error_result(
                "Curve(s) not found: {}".format(", ".join(missing_curves)),
                "Ensure all curves exist in the scene",
            ).to_dict()

        missing_objects = [o for o in objects if not cmds.objExists(o)]
        if missing_objects:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing_objects)),
                "Ensure all objects exist in the scene",
            ).to_dict()

        wire_kwargs = {
            "wire": curves,
            "dropoffDistance": [(i, dropoff_distance) for i in range(len(curves))],
        }  # type: Dict
        if name:
            wire_kwargs["name"] = name

        result = cmds.wire(objects, **wire_kwargs)
        wire_node = result[0] if result else None

        return success_result(
            "Created wire deformer '{}' on {} object(s)".format(wire_node, len(objects)),
            wire_node=wire_node,
            curves=list(curves),
            objects=list(objects),
            dropoff_distance=dropoff_distance,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("wire_deformer failed")
        return error_result("Failed to create wire deformer", str(exc)).to_dict()


def sculpt_deformer(
    objects: List[str],
    name: Optional[str] = None,
    mode: str = "stretch",
    max_displacement: float = 1.0,
) -> dict:
    """Create a sculpt deformer on one or more objects.

    The sculpt deformer displaces vertices based on a sculpt sphere that can
    stretch, project, or flip the surface geometry.

    Args:
        objects: List of mesh names to deform.
        name: Optional base name for the sculpt/sphere nodes.
        mode: Deformation mode — ``"stretch"`` (0), ``"project"`` (1), or
            ``"flip"`` (2).  Default: ``"stretch"``.
        max_displacement: Maximum vertex displacement amount.  Default: ``1.0``.

    Returns:
        ActionResultModel dict with ``context.sculpt_node``,
        ``context.sculpt_sphere``, ``context.sculpt_origin``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    mode_map = {"stretch": 0, "project": 1, "flip": 2}
    mode_lower = mode.lower()
    if mode_lower not in mode_map:
        return error_result(
            "Invalid mode: {}".format(mode),
            "Valid modes: {}".format(", ".join(mode_map.keys())),
        ).to_dict()

    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one mesh name in 'objects'",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist in the scene",
            ).to_dict()

        sculpt_kwargs = {
            "mode": mode_map[mode_lower],
            "maxDisplacement": max_displacement,
        }  # type: Dict
        if name:
            sculpt_kwargs["name"] = name

        result = cmds.sculpt(objects, **sculpt_kwargs)
        # cmds.sculpt returns [sculptNode, sculptSphere, sculptOrigin]
        sculpt_node = result[0] if result else None
        sculpt_sphere = result[1] if result and len(result) > 1 else None
        sculpt_origin = result[2] if result and len(result) > 2 else None

        return success_result(
            "Created sculpt deformer '{}' (mode='{}') on {} object(s)".format(sculpt_node, mode_lower, len(objects)),
            sculpt_node=sculpt_node,
            sculpt_sphere=sculpt_sphere,
            sculpt_origin=sculpt_origin,
            objects=list(objects),
            mode=mode_lower,
            max_displacement=max_displacement,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("sculpt_deformer failed")
        return error_result("Failed to create sculpt deformer", str(exc)).to_dict()
