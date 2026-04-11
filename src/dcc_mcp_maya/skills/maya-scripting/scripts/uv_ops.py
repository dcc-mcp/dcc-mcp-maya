"""Maya UV operation actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_uv_info(object_name: str, uv_set: Optional[str] = None) -> dict:
    """Query UV sets and coordinates on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set: UV set name to query coordinates from.  If None, returns
            info about all UV sets without coordinate data.

    Returns:
        ActionResultModel dict with ``context.uv_sets``, ``context.current_uv_set``,
        and optionally ``context.uv_count`` / ``context.uvs``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        uv_sets = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        current_set = cmds.polyUVSet(object_name, query=True, currentUVSet=True)
        if isinstance(current_set, list):
            current_set = current_set[0] if current_set else None

        result_kwargs = {
            "uv_sets": uv_sets,
            "current_uv_set": current_set,
            "uv_set_count": len(uv_sets),
        }  # type: Dict

        if uv_set:
            if uv_set not in uv_sets:
                return error_result("UV set '{}' not found on '{}'".format(uv_set, object_name)).to_dict()
            u_coords = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, uValue=True) or []
            result_kwargs["uv_count"] = len(u_coords)
            result_kwargs["queried_uv_set"] = uv_set

        return success_result("UV info for '{}'".format(object_name), **result_kwargs).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_uv_info failed")
        return error_result("Failed to get UV info", str(exc)).to_dict()


def create_uv_set(object_name: str, uv_set_name: str, copy_from: Optional[str] = None) -> dict:
    """Create a new UV set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name for the new UV set.
        copy_from: Optional existing UV set name to copy UVs from.

    Returns:
        ActionResultModel dict with ``context.uv_set_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name in existing:
            return error_result("UV set '{}' already exists on '{}'".format(uv_set_name, object_name)).to_dict()

        if copy_from:
            if copy_from not in existing:
                return error_result("Source UV set '{}' not found on '{}'".format(copy_from, object_name)).to_dict()
            cmds.polyUVSet(object_name, copy=True, uvSet=copy_from, newUVSet=uv_set_name)
        else:
            cmds.polyUVSet(object_name, create=True, uvSet=uv_set_name)

        return success_result(
            "Created UV set '{}' on '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
            copied_from=copy_from,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_uv_set failed")
        return error_result("Failed to create UV set", str(exc)).to_dict()


def delete_uv_set(object_name: str, uv_set_name: str) -> dict:
    """Delete a UV set from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name of the UV set to delete.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name not in existing:
            return error_result("UV set '{}' not found on '{}'".format(uv_set_name, object_name)).to_dict()

        # Protect the only remaining UV set
        if len(existing) <= 1:
            return error_result("Cannot delete the only UV set on '{}'".format(object_name)).to_dict()

        cmds.polyUVSet(object_name, delete=True, uvSet=uv_set_name)

        return success_result(
            "Deleted UV set '{}' from '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("delete_uv_set failed")
        return error_result("Failed to delete UV set", str(exc)).to_dict()


def project_uvs(
    object_name: str,
    projection_type: str = "planar",
    axis: str = "y",
) -> dict:
    """Apply a UV projection to a polygon mesh.

    Args:
        object_name: Transform or mesh name.
        projection_type: Projection type — ``"planar"``, ``"cylindrical"``,
            or ``"spherical"``.  Default: ``"planar"``.
        axis: Projection axis — ``"x"``, ``"y"``, or ``"z"``.  Only used
            for planar and cylindrical projections.  Default: ``"y"``.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    valid_types = ("planar", "cylindrical", "spherical")
    if projection_type not in valid_types:
        return error_result(
            "Invalid projection_type: {}".format(projection_type),
            "Use one of: {}".format(", ".join(valid_types)),
        ).to_dict()

    valid_axes = ("x", "y", "z")
    if axis not in valid_axes:
        return error_result(
            "Invalid axis: {}".format(axis),
            "Use one of: x, y, z",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        axis_index = {"x": 0, "y": 1, "z": 2}[axis]

        if projection_type == "planar":
            cmds.polyProjection(
                object_name,
                type="Planar",
                mapDirection=axis.upper(),
                ch=False,
            )
        elif projection_type == "cylindrical":
            cmds.polyProjection(
                object_name,
                type="Cylindrical",
                ch=False,
            )
        else:
            cmds.polyProjection(
                object_name,
                type="Spherical",
                ch=False,
            )

        return success_result(
            "Applied {} UV projection to '{}' (axis={})".format(projection_type, object_name, axis),
            object_name=object_name,
            projection_type=projection_type,
            axis=axis,
            axis_index=axis_index,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("project_uvs failed")
        return error_result("Failed to project UVs", str(exc)).to_dict()


def copy_uvs(
    source: str,
    target: str,
    source_uv_set: Optional[str] = None,
    target_uv_set: Optional[str] = None,
) -> dict:
    """Copy UV layout from one mesh to another via polyTransfer.

    Args:
        source: Source mesh transform or shape name.
        target: Target mesh transform or shape name.
        source_uv_set: UV set on the source to copy from.  If None, uses
            the current UV set.
        target_uv_set: UV set on the target to copy into.  If None, uses
            the current UV set.

    Returns:
        ActionResultModel dict.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (source, target):
            if not cmds.objExists(name):
                return error_result("Object not found: {}".format(name)).to_dict()

        kwargs = {
            "transferUVs": 1,
            "sampleSpace": 4,  # UV space
            "ch": False,
        }  # type: Dict
        if source_uv_set:
            kwargs["sourceUvSet"] = source_uv_set
        if target_uv_set:
            kwargs["targetUvSet"] = target_uv_set

        cmds.transferAttributes(source, target, **kwargs)

        return success_result(
            "Copied UVs from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            source_uv_set=source_uv_set,
            target_uv_set=target_uv_set,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("copy_uvs failed")
        return error_result("Failed to copy UVs", str(exc)).to_dict()


def get_uv_shell_info(object_name: str, uv_set: Optional[str] = None) -> dict:
    """Get UV shell information for a polygon mesh.

    Reports the number of UV shells and the bounding box of each shell in
    UV space (u_min, v_min, u_max, v_max).

    Args:
        object_name: Transform or mesh shape name.
        uv_set: UV set to query.  If None, uses the current active UV set.

    Returns:
        ActionResultModel dict with ``context.shell_count``,
        ``context.shells`` (list of dicts with ``u_min``, ``v_min``,
        ``u_max``, ``v_max``, ``uv_indices``).
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        # Resolve UV set
        if uv_set:
            existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
            if uv_set not in existing:
                return error_result("UV set '{}' not found on '{}'".format(uv_set, object_name)).to_dict()
            cmds.polyUVSet(object_name, currentUVSet=True, uvSet=uv_set)

        active_set = cmds.polyUVSet(object_name, query=True, currentUVSet=True)
        if isinstance(active_set, list):
            active_set = active_set[0] if active_set else "map1"

        # Query UV shell IDs per UV component
        shell_ids = cmds.polyEvaluate(object_name, uvShellsIds=True) or []

        # Build shell groups: shell_id -> list of UV component indices
        shell_map = {}  # type: Dict[int, List[int]]
        for i, sid in enumerate(shell_ids):
            shell_map.setdefault(int(sid), []).append(i)

        # Query all U and V coordinates
        u_vals = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, uValue=True) or []
        v_vals = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, vValue=True) or []

        shells = []
        for sid in sorted(shell_map.keys()):
            indices = shell_map[sid]
            us = [u_vals[i] for i in indices if i < len(u_vals)]
            vs = [v_vals[i] for i in indices if i < len(v_vals)]
            if us and vs:
                shells.append(
                    {
                        "shell_id": sid,
                        "uv_count": len(indices),
                        "u_min": min(us),
                        "u_max": max(us),
                        "v_min": min(vs),
                        "v_max": max(vs),
                    }
                )
            else:
                shells.append({"shell_id": sid, "uv_count": len(indices)})

        return success_result(
            "UV shell info for '{}' (UV set: {})".format(object_name, active_set),
            object_name=object_name,
            uv_set=active_set,
            shell_count=len(shells),
            shells=shells,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_uv_shell_info failed")
        return error_result("Failed to get UV shell info", str(exc)).to_dict()


def unfold_uvs(
    object_name: str,
    iterations: int = 1,
    optimize_scale: bool = True,
) -> dict:
    """Unfold the UV layout on a polygon mesh.

    Uses ``cmds.u3dUnfold`` to iteratively unfold UV shells.

    Args:
        object_name: Transform or mesh shape name.
        iterations: Number of unfold iterations (1–100).  Default: 1.
        optimize_scale: When True, normalises UV shells after unfolding so
            they all have the same texel density.  Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``,
        ``context.iterations``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if iterations < 1 or iterations > 100:
        return error_result(
            "Invalid iterations: {}".format(iterations),
            "iterations must be between 1 and 100",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        cmds.u3dUnfold(
            object_name,
            iterations=iterations,
            pack=False,
            borderintersection=True,
            triangleflip=True,
            mapsize=512,
            roomspace=0,
        )

        if optimize_scale:
            cmds.u3dOptimize(object_name, iterations=1, power=1, resultScale=1)

        return success_result(
            "Unfolded UVs on '{}' ({} iteration(s))".format(object_name, iterations),
            object_name=object_name,
            iterations=iterations,
            optimize_scale=optimize_scale,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("unfold_uvs failed")
        return error_result("Failed to unfold UVs on '{}'".format(object_name), str(exc)).to_dict()


def normalize_uvs(
    object_name: str,
    layout_u: float = 1.0,
    layout_v: float = 1.0,
    preserve_aspect: bool = True,
) -> dict:
    """Normalize UV coordinates to fit within the 0-1 UV tile.

    Args:
        object_name: Transform or mesh shape name.
        layout_u: Target U dimension (0 < value <= 1).  Default: 1.0.
        layout_v: Target V dimension (0 < value <= 1).  Default: 1.0.
        preserve_aspect: When True, scale uniformly to preserve aspect ratio.
            Default: True.

    Returns:
        ActionResultModel dict with ``context.object_name``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not (0 < layout_u <= 1):
        return error_result(
            "Invalid layout_u: {}".format(layout_u),
            "layout_u must be in range (0, 1]",
        ).to_dict()
    if not (0 < layout_v <= 1):
        return error_result(
            "Invalid layout_v: {}".format(layout_v),
            "layout_v must be in range (0, 1]",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return error_result("Object not found: {}".format(object_name)).to_dict()

        cmds.polyNormalizeUV(
            object_name,
            normalizeType=1,
            preserveAspectRatio=preserve_aspect,
            centerOnTile=True,
            ch=False,
        )

        return success_result(
            "Normalized UVs on '{}' (layout_u={}, layout_v={})".format(object_name, layout_u, layout_v),
            object_name=object_name,
            layout_u=layout_u,
            layout_v=layout_v,
            preserve_aspect=preserve_aspect,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("normalize_uvs failed")
        return error_result("Failed to normalize UVs on '{}'".format(object_name), str(exc)).to_dict()
