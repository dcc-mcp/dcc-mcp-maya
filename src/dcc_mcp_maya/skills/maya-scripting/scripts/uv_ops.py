"""Maya UV operation actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_error, skill_exception, skill_success


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

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
                return skill_error("UV set '{}' not found on '{}'".format(uv_set, object_name))
            u_coords = cmds.polyEditUV("{}.map[*]".format(object_name), query=True, uValue=True) or []
            result_kwargs["uv_count"] = len(u_coords)
            result_kwargs["queried_uv_set"] = uv_set

        return skill_success(
            "UV info for '{}'".format(object_name),
            **result_kwargs,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get UV info")


def create_uv_set(object_name: str, uv_set_name: str, copy_from: Optional[str] = None) -> dict:
    """Create a new UV set on a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name for the new UV set.
        copy_from: Optional existing UV set name to copy UVs from.

    Returns:
        ActionResultModel dict with ``context.uv_set_name``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name in existing:
            return skill_error("UV set '{}' already exists on '{}'".format(uv_set_name, object_name))

        if copy_from:
            if copy_from not in existing:
                return skill_error("Source UV set '{}' not found on '{}'".format(copy_from, object_name))
            cmds.polyUVSet(object_name, copy=True, uvSet=copy_from, newUVSet=uv_set_name)
        else:
            cmds.polyUVSet(object_name, create=True, uvSet=uv_set_name)

        return skill_success(
            "Created UV set '{}' on '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
            copied_from=copy_from,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create UV set")


def delete_uv_set(object_name: str, uv_set_name: str) -> dict:
    """Delete a UV set from a polygon mesh.

    Args:
        object_name: Transform or mesh shape name.
        uv_set_name: Name of the UV set to delete.

    Returns:
        ActionResultModel dict.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

        existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
        if uv_set_name not in existing:
            return skill_error("UV set '{}' not found on '{}'".format(uv_set_name, object_name))

        # Protect the only remaining UV set
        if len(existing) <= 1:
            return skill_error("Cannot delete the only UV set on '{}'".format(object_name))

        cmds.polyUVSet(object_name, delete=True, uvSet=uv_set_name)

        return skill_success(
            "Deleted UV set '{}' from '{}'".format(uv_set_name, object_name),
            object_name=object_name,
            uv_set_name=uv_set_name,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to delete UV set")


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

    valid_types = ("planar", "cylindrical", "spherical")
    if projection_type not in valid_types:
        return skill_error(
            "Invalid projection_type: {}".format(projection_type),
            "Use one of: {}".format(", ".join(valid_types)),
        )

    valid_axes = ("x", "y", "z")
    if axis not in valid_axes:
        return skill_error(
            "Invalid axis: {}".format(axis),
            "Use one of: x, y, z",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

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

        return skill_success(
            "Applied {} UV projection to '{}' (axis={})".format(projection_type, object_name, axis),
            object_name=object_name,
            projection_type=projection_type,
            axis=axis,
            axis_index=axis_index,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to project UVs")


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (source, target):
            if not cmds.objExists(name):
                return skill_error("Object not found: {}".format(name))

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

        return skill_success(
            "Copied UVs from '{}' to '{}'".format(source, target),
            source=source,
            target=target,
            source_uv_set=source_uv_set,
            target_uv_set=target_uv_set,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to copy UVs")


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

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

        # Resolve UV set
        if uv_set:
            existing = cmds.polyUVSet(object_name, query=True, allUVSets=True) or []
            if uv_set not in existing:
                return skill_error("UV set '{}' not found on '{}'".format(uv_set, object_name))
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

        return skill_success(
            "UV shell info for '{}' (UV set: {})".format(object_name, active_set),
            object_name=object_name,
            uv_set=active_set,
            shell_count=len(shells),
            shells=shells,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get UV shell info")


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

    if iterations < 1 or iterations > 100:
        return skill_error(
            "Invalid iterations: {}".format(iterations),
            "iterations must be between 1 and 100",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

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

        return skill_success(
            "Unfolded UVs on '{}' ({} iteration(s))".format(object_name, iterations),
            object_name=object_name,
            iterations=iterations,
            optimize_scale=optimize_scale,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to unfold UVs on '{}'".format(object_name))


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

    if not (0 < layout_u <= 1):
        return skill_error(
            "Invalid layout_u: {}".format(layout_u),
            "layout_u must be in range (0, 1]",
        )
    if not (0 < layout_v <= 1):
        return skill_error(
            "Invalid layout_v: {}".format(layout_v),
            "layout_v must be in range (0, 1]",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(object_name):
            return skill_error("Object not found: {}".format(object_name))

        cmds.polyNormalizeUV(
            object_name,
            normalizeType=1,
            preserveAspectRatio=preserve_aspect,
            centerOnTile=True,
            ch=False,
        )

        return skill_success(
            "Normalized UVs on '{}' (layout_u={}, layout_v={})".format(object_name, layout_u, layout_v),
            object_name=object_name,
            layout_u=layout_u,
            layout_v=layout_v,
            preserve_aspect=preserve_aspect,
            prompt="Check the result with list_scripting or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to normalize UVs on '{}'".format(object_name))
