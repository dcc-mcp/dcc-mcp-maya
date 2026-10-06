"""Import an AssetDescriptor into the current Maya scene.

Handles FBX, OBJ, USD (usda/usdc), Maya ASCII/Binary formats.
Post-import operations:
  - Axis conversion   (y_to_z / z_to_y via cmds.xform)
  - Unit scale        (uniform cmds.xform scale)
  - MaterialMode      (preserve / assign_lambert / skip)
  - PlacementHint     (origin / selection / custom)
  - target_collection (add top-level nodes to an existing set or group)
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

# Import third-party modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Format → Maya file type string + required plugin
# ---------------------------------------------------------------------------
_FORMAT_TYPE: Dict[str, str] = {
    "fbx": "FBX",
    "obj": "OBJ",
    "usd": "USD Import",
    "usda": "USD Import",
    "usdc": "USD Import",
    "ma": "mayaAscii",
    "mb": "mayaBinary",
}

_FORMAT_PLUGIN: Dict[str, str] = {
    "fbx": "fbxmaya",
    "obj": "objExport",
    "usd": "mayaUsdPlugin",
    "usda": "mayaUsdPlugin",
    "usdc": "mayaUsdPlugin",
}

# Axis conversion: rotation around X in degrees
_AXIS_ROTATION: Dict[str, float] = {
    "y_to_z": 90.0,
    "z_to_y": -90.0,
}

# ---------------------------------------------------------------------------
# Unit / up-axis semantics
# ---------------------------------------------------------------------------

#: Linear units Maya reports from ``currentUnit``, expressed in centimetres
#: (Maya's internal linear unit). Converting a declared source unit into the
#: target scene's unit is a ratio of these two values.
_UNIT_TO_CM: Dict[str, float] = {
    "mm": 0.1,
    "cm": 1.0,
    "m": 100.0,
    "km": 100000.0,
    "in": 2.54,
    "ft": 30.48,
    "yd": 91.44,
    "mi": 160934.4,
}

#: Up-axis values understood by ``upAxis``.
_UP_AXES = ("y", "z")

#: File formats that carry **no** unit and **no** up-axis metadata.
#:
#: These are the dangerous ones: the numbers arrive as bare floats, so Maya
#: silently reads them in the target scene's unit and orientation. An OBJ
#: authored in metres lands 100x too small in a centimetre scene, and a Z-up
#: file lies down in a Y-up scene -- with geometry fully intact, so nothing
#: looks broken. These formats must warn when the caller does not declare
#: semantics; formats that carry their own metadata (FBX, USD, MA, MB) do not.
_FORMAT_WITHOUT_SEMANTICS = frozenset({"obj"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_path(path: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded.replace("\\", "/")


def _ensure_plugin(cmds: Any, plugin_name: str) -> None:
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def _short_name(node: str) -> str:
    return node.rsplit("|", 1)[-1] if "|" in node else node


def _select_difference(before: Sequence[str], after: Sequence[str]) -> List[str]:
    before_set = set(before)
    return [n for n in after if n not in before_set]


def _top_level_transforms(new_long: List[str], cmds: Any) -> List[str]:
    """Return world-root transform nodes from newly imported nodes."""
    result = []
    for n in new_long:
        if n.count("|") == 1:
            try:
                if cmds.objectType(n) == "transform":
                    result.append(n)
            except Exception:  # noqa: BLE001
                pass
    return result


def _scene_linear_unit(cmds: Any) -> str:
    """Return the target scene's linear unit (``cm``, ``m``, ...) or ``""``."""
    try:
        unit = cmds.currentUnit(query=True, linear=True)
    except Exception:  # noqa: BLE001
        return ""
    return str(unit).strip().lower() if unit else ""


def _scene_up_axis(cmds: Any) -> str:
    """Return the target scene's up axis (``y`` or ``z``) or ``""``."""
    try:
        axis = cmds.upAxis(query=True, axis=True)
    except Exception:  # noqa: BLE001
        return ""
    return str(axis).strip().lower() if axis else ""


def _resolve_import_semantics(  # noqa: PLR0912
    cmds: Any,
    fmt: str,
    source_unit: Optional[str],
    source_up_axis: Optional[str],
    axis_conversion: str,
) -> Dict[str, Any]:
    """Decide how -- and whether -- to convert units and up-axis.

    The caller may declare what the *file* is authored in. When they do, the
    values are converted into the target scene. When they do not and the format
    cannot carry that metadata either, the import is still performed but the
    assumption is reported instead of being swallowed.

    Formats without unit metadata are read by Maya in its internal unit, which
    is always centimetres, so a declared source unit converts straight to
    centimetres -- the target scene's unit does not enter into it.

    Declarative conversion is only applied to formats that cannot carry the
    metadata themselves (see ``_FORMAT_WITHOUT_SEMANTICS``). FBX, USD and the
    Maya formats describe their own units and up axis, and Maya's importers
    apply that on import -- measured on Maya 2026, a metres-authored FBX lands
    at 100 cm in a centimetre scene, and a Y-up file lands height-on-Z in a
    Z-up scene. Scaling or rotating again would double-apply, which is the
    very class of silent error this tool exists to prevent. A declaration on
    such a format is reported as ignored rather than applied.

    Returns a dict with ``errors`` (fatal), ``warnings`` (non-fatal),
    ``blocking_warnings`` (the subset that ``require_semantics`` refuses on),
    ``unit_factor``, ``axis_conversion``, plus the resolved source/target
    values so the result can be audited after the fact.
    """
    errors: List[str] = []
    warnings: List[str] = []
    # Assumptions the caller did not authorise. Kept separate from ``warnings``
    # so an advisory "your declaration was ignored" note never trips
    # ``require_semantics``: that flag refuses *undeclared* imports, and a
    # self-describing format is not importing under an assumption.
    blocking_warnings: List[str] = []
    # Does the format carry its own unit / up-axis metadata?
    self_describing = fmt not in _FORMAT_WITHOUT_SEMANTICS

    target_unit = _scene_linear_unit(cmds)
    target_up_axis = _scene_up_axis(cmds)
    declared_unit = (source_unit or "").strip().lower() or None
    declared_axis = (source_up_axis or "").strip().lower() or None

    if declared_unit is not None and declared_unit not in _UNIT_TO_CM:
        errors.append("Unknown source_unit '{}'. Supported: {}".format(declared_unit, ", ".join(sorted(_UNIT_TO_CM))))
        declared_unit = None

    if declared_axis is not None and declared_axis not in _UP_AXES:
        errors.append("Unknown source_up_axis '{}'. Supported: y, z".format(declared_axis))
        declared_axis = None

    # -- Unit ---------------------------------------------------------------
    # Maya reads a format without unit metadata in its INTERNAL unit, which is
    # always centimetres -- currentUnit only changes how those centimetres are
    # displayed, not how they are read. Measured on Maya 2026: one hand-written
    # OBJ imported into cm / mm / m / km / in scenes measures [1, 2, 3] cm in
    # every one of them. So converting a declared source unit is a straight
    # unit -> centimetres conversion; dividing by the target scene unit (as an
    # earlier version did) is only correct when that unit happens to be cm,
    # and silently under-scales by up to 1e5 otherwise.
    unit_factor = 1.0
    if declared_unit and self_describing:
        # The importer already converted the file's own units into the scene
        # unit. Applying the declared factor on top would scale twice.
        warnings.append(
            "source_unit='{}' was ignored: {} files carry their own units and Maya's importer "
            "already converted them into the scene unit ('{}'). Use unit_scale for a manual "
            "override.".format(declared_unit, fmt.upper(), target_unit or "unknown")
        )
    elif declared_unit:
        unit_factor = _UNIT_TO_CM[declared_unit]
    elif fmt in _FORMAT_WITHOUT_SEMANTICS:
        # Neither the file nor the caller knows. Maya has already read the bare
        # numbers as centimetres, so state that assumption out loud rather than
        # letting a 100x error pass as a clean import. This one is an
        # unauthorised assumption, so require_semantics refuses on it.
        blocking_warnings.append(
            "Source file declares no unit and source_unit was not given; values were "
            "interpreted as centimetres (Maya's internal unit, whatever the scene unit is). "
            "Pass source_unit to convert."
        )

    # -- Up axis ------------------------------------------------------------
    resolved_axis = axis_conversion or "none"
    if declared_axis and self_describing:
        # Same reasoning as units: the importer aligned the up axis already.
        warnings.append(
            "source_up_axis='{}' was ignored: {} files carry their own up axis and Maya's "
            "importer already aligned it to the scene ('{}'). Use axis_conversion for a "
            "manual override.".format(declared_axis, fmt.upper(), target_up_axis or "unknown")
        )
    elif declared_axis and not target_up_axis:
        warnings.append(
            "Cannot determine the target scene up-axis, so source_up_axis='{}' was ignored.".format(declared_axis)
        )
    elif resolved_axis == "none" and declared_axis and declared_axis != target_up_axis:
        resolved_axis = "z_to_y" if declared_axis == "z" else "y_to_z"

    if not declared_axis and fmt in _FORMAT_WITHOUT_SEMANTICS:
        blocking_warnings.append(
            "Source file declares no up-axis and source_up_axis was not given; the geometry "
            "was imported as authored, which is {}-up in this scene. Pass source_up_axis "
            "('y' or 'z') to convert.".format(target_up_axis or "unknown")
        )

    warnings = warnings + blocking_warnings
    return {
        "errors": errors,
        "warnings": warnings,
        "blocking_warnings": blocking_warnings,
        "unit_factor": unit_factor,
        "axis_conversion": resolved_axis,
        "source_unit": declared_unit,
        "source_up_axis": declared_axis,
        "target_unit": target_unit,
        "target_up_axis": target_up_axis,
    }


def _announce_warnings(cmds: Any, warnings: List[str]) -> None:
    """Mirror warnings into Maya's Script Editor so they reach the operator."""
    for message in warnings:
        logger.warning("%s", message)
        try:
            cmds.warning("[import_to_scene] {}".format(message))
        except Exception:  # noqa: BLE001
            pass


def _apply_axis_conversion(cmds: Any, nodes: List[str], axis_conversion: str) -> None:
    """Rotate each top-level transform to correct axis orientation."""
    rotation_x = _AXIS_ROTATION.get(axis_conversion)
    if rotation_x is None:
        return
    for node in nodes:
        try:
            current = cmds.xform(node, query=True, rotation=True, worldSpace=True) or [0.0, 0.0, 0.0]
            cmds.xform(node, rotation=[current[0] + rotation_x, current[1], current[2]], worldSpace=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("axis_conversion xform failed on %s: %s", node, exc)


def _apply_unit_scale(cmds: Any, nodes: List[str], unit_scale: float) -> None:
    """Apply a uniform scale factor to each top-level transform."""
    if unit_scale == 1.0:
        return
    for node in nodes:
        try:
            current = cmds.xform(node, query=True, scale=True, worldSpace=True) or [1.0, 1.0, 1.0]
            cmds.xform(
                node,
                scale=[current[0] * unit_scale, current[1] * unit_scale, current[2] * unit_scale],
                worldSpace=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("unit_scale xform failed on %s: %s", node, exc)


def _get_mesh_shapes(cmds: Any, new_long: List[str]) -> List[str]:
    """Collect all mesh shape nodes from newly imported nodes."""
    shapes = []
    for n in new_long:
        try:
            if cmds.objectType(n) == "mesh":
                shapes.append(n)
        except Exception:  # noqa: BLE001
            pass
    return shapes


def _apply_material_mode(cmds: Any, new_long: List[str], material_mode: str) -> None:
    """Apply material mode to newly imported mesh shapes."""
    if material_mode == "preserve":
        return

    shapes = _get_mesh_shapes(cmds, new_long)
    if not shapes:
        return

    if material_mode == "assign_lambert":
        try:
            lambert = cmds.shadingNode("lambert", asShader=True, name="dcc_mcp_import_lambert")
            shading_group = cmds.sets(
                renderable=True, noSurfaceShader=True, empty=True, name="dcc_mcp_import_lambertSG"
            )
            cmds.connectAttr("{}.outColor".format(lambert), "{}.surfaceShader".format(shading_group), force=True)
            for shape in shapes:
                cmds.sets(shape, edit=True, forceElement=shading_group)
        except Exception as exc:  # noqa: BLE001
            logger.warning("assign_lambert failed: %s", exc)

    elif material_mode == "skip":
        try:
            default_sg = "initialShadingGroup"
            for shape in shapes:
                try:
                    cmds.sets(shape, edit=True, forceElement=default_sg)
                except Exception:  # noqa: BLE001
                    pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("skip material mode failed: %s", exc)


def _apply_placement_hint(
    cmds: Any,
    top_nodes: List[str],
    placement_hint: str,
    custom_position: Optional[List[float]],
) -> None:
    """Move top-level transforms according to the placement hint."""
    if placement_hint == "origin" or not top_nodes:
        return

    if placement_hint == "selection":
        selection = cmds.ls(selection=True) or []
        if not selection:
            logger.warning("placement_hint=selection but nothing is selected; skipping placement")
            return
        try:
            pivot = cmds.xform(selection[0], query=True, worldSpace=True, rotatePivot=True) or [0.0, 0.0, 0.0]
        except Exception:  # noqa: BLE001
            logger.warning("Could not get selection pivot; skipping placement")
            return
        target_pos = pivot[:3]

    elif placement_hint == "custom":
        if not custom_position or len(custom_position) < 3:
            logger.warning("placement_hint=custom but custom_position not provided; skipping placement")
            return
        target_pos = list(custom_position[:3])
    else:
        return

    # Move each top-level node
    for node in top_nodes:
        try:
            cmds.xform(node, translation=target_pos, worldSpace=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("placement xform failed on %s: %s", node, exc)


def _apply_target_collection(cmds: Any, top_nodes: List[str], target_collection: str) -> None:
    """Add top-level transforms to an existing Maya set or group."""
    if not target_collection or not top_nodes:
        return
    try:
        if cmds.objExists(target_collection):
            node_type = cmds.objectType(target_collection)
            if node_type == "objectSet":
                cmds.sets(top_nodes, edit=True, addElement=target_collection)
            elif node_type == "transform":
                for n in top_nodes:
                    cmds.parent(n, target_collection)
            else:
                logger.warning(
                    "target_collection '%s' has type '%s'; expected objectSet or transform",
                    target_collection,
                    node_type,
                )
        else:
            logger.warning("target_collection '%s' does not exist in the scene", target_collection)
    except Exception as exc:  # noqa: BLE001
        logger.warning("target_collection failed: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def import_to_scene(  # noqa: PLR0913
    asset: Dict[str, Any],
    namespace: Optional[str] = None,
    group_name: Optional[str] = None,
    axis_conversion: str = "none",
    unit_scale: float = 1.0,
    material_mode: str = "preserve",
    placement_hint: str = "origin",
    custom_position: Optional[List[float]] = None,
    target_collection: Optional[str] = None,
    merge_namespaces: bool = False,
    source_unit: Optional[str] = None,
    source_up_axis: Optional[str] = None,
    require_semantics: bool = False,
) -> Dict[str, Any]:
    """Import *asset* into the current Maya scene.

    Parameters
    ----------
    asset
        AssetDescriptor dict from maya-asset-source.  Requires at minimum
        ``path`` and ``format`` keys.
    namespace
        Optional namespace prefix to keep imported nodes separable.
    group_name
        Optional wrapper transform name for all imported top-level nodes.
    axis_conversion
        Post-import axis correction: ``none``, ``y_to_z``, or ``z_to_y``.
    unit_scale
        Uniform scale applied to top-level transforms after import.
        ``1.0`` means no change.
    material_mode
        ``preserve`` (default), ``assign_lambert``, or ``skip``.
    placement_hint
        ``origin`` (default), ``selection``, or ``custom``.
    custom_position
        [x, y, z] world-space translation when ``placement_hint == "custom"``.
    target_collection
        Name of an existing objectSet or group transform to add imported
        top-level nodes to.
    merge_namespaces
        Reuse an existing namespace rather than appending a numeric suffix.
    source_unit
        Linear unit the *file* is authored in (``mm``, ``cm``, ``m``, ``km``,
        ``in``, ``ft``, ``yd``, ``mi``). When given, values are scaled so they
        become centimetres -- Maya's internal unit, which is how a format
        without unit metadata is read regardless of ``currentUnit``. When
        omitted, no conversion happens -- and for formats that cannot carry
        unit metadata (OBJ) a warning records the assumption instead of
        failing silently. Only applies to formats without their own unit
        metadata; on FBX / USD / MA / MB the importer has already converted,
        so the declaration is reported as ignored.
    source_up_axis
        Up axis the *file* is authored in (``y`` or ``z``). When it differs
        from the target scene's up axis the import is rotated to match.
    require_semantics
        Refuse to import (instead of warning) when the source unit or up axis
        is undeclared for a format that cannot carry that metadata.

    Returns
    -------
    dict
        Success envelope with ``context`` holding an ``ImportToSceneResult``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # ------------------------------------------------------------------
        # Validate asset descriptor
        # ------------------------------------------------------------------
        if not asset:
            return skill_error("Missing asset", "asset descriptor is required")

        path = asset.get("path", "")
        fmt = (asset.get("format") or "").lower()

        if not path:
            return skill_error("Missing asset.path", "asset.path is required")
        if not fmt:
            return skill_error("Missing asset.format", "asset.format is required")
        if fmt not in _FORMAT_TYPE:
            return skill_error(
                "Unsupported format",
                "Format '{}' is not supported. Supported: {}".format(fmt, ", ".join(sorted(_FORMAT_TYPE))),
                format=fmt,
            )

        normalized = _normalize_path(path)
        if not os.path.isfile(normalized):
            return skill_error(
                "Asset file not found",
                "{} does not exist on disk".format(normalized),
                path=normalized,
                possible_solutions=["Verify the path in the AssetDescriptor"],
            )

        # ------------------------------------------------------------------
        # Load required plugin
        # ------------------------------------------------------------------
        plugin = _FORMAT_PLUGIN.get(fmt)
        if plugin:
            try:
                _ensure_plugin(cmds, plugin)
            except Exception as exc:  # noqa: BLE001
                return skill_error(
                    "Plugin unavailable",
                    "loadPlugin('{}') failed: {}".format(plugin, exc),
                    format=fmt,
                    plugin=plugin,
                )

        # Extra FBX reset before import
        if fmt == "fbx":
            import maya.mel as mel  # noqa: PLC0415

            mel.eval("FBXResetImport")
            mel.eval("FBXImportMode -v add")
            mel.eval("FBXImportMergeAnimationLayers -v true")
            mel.eval("FBXImportGenerateLog -v false")

        # ------------------------------------------------------------------
        # Resolve unit / up-axis semantics before touching the scene
        # ------------------------------------------------------------------
        semantics = _resolve_import_semantics(cmds, fmt, source_unit, source_up_axis, axis_conversion)

        if semantics["errors"]:
            return skill_error(
                " ".join(semantics["errors"]),
                "invalid_import_semantics",
                errors=semantics["errors"],
                possible_solutions=[
                    "source_unit accepts: {}".format(", ".join(sorted(_UNIT_TO_CM))),
                    "source_up_axis accepts: y, z",
                ],
            )

        # Only *unauthorised* assumptions block. A note that a declaration was
        # ignored on a self-describing format is advisory, not an assumption.
        if require_semantics and semantics["blocking_warnings"]:
            return skill_error(
                "Refusing to import with an assumption: {}".format(" ".join(semantics["blocking_warnings"])),
                "undeclared_import_semantics",
                warnings=semantics["blocking_warnings"],
                possible_solutions=[
                    "Pass source_unit and source_up_axis so the values can be converted, "
                    "or set require_semantics=False to import with the stated assumption."
                ],
            )

        _announce_warnings(cmds, semantics["warnings"])
        resolved_axis_conversion = semantics["axis_conversion"]
        resolved_unit_scale = unit_scale * semantics["unit_factor"]

        # ------------------------------------------------------------------
        # Snapshot scene before import
        # ------------------------------------------------------------------
        before = cmds.ls(long=True) or []

        # ------------------------------------------------------------------
        # Run import
        # ------------------------------------------------------------------
        file_type = _FORMAT_TYPE[fmt]
        import_kwargs: Dict[str, Any] = {
            "i": True,
            "type": file_type,
            "ignoreVersion": True,
            "preserveReferences": True,
            "prompt": False,
        }
        if namespace:
            import_kwargs["namespace"] = namespace
            import_kwargs["mergeNamespacesOnClash"] = bool(merge_namespaces)

        try:
            cmds.file(normalized, **import_kwargs)
        except RuntimeError as exc:
            return skill_exception(exc, message="cmds.file import raised", path=normalized, format=fmt)

        # ------------------------------------------------------------------
        # Compute new nodes
        # ------------------------------------------------------------------
        after = cmds.ls(long=True) or []
        new_long = _select_difference(before, after)
        new_short = sorted({_short_name(n) for n in new_long})
        top_nodes = _top_level_transforms(new_long, cmds)

        # ------------------------------------------------------------------
        # Optional post-import grouping
        # ------------------------------------------------------------------
        top_level_groups: List[str] = []
        if group_name and top_nodes:
            try:
                created_group = cmds.group(top_nodes, name=group_name, world=True)
                top_nodes = [created_group]
                top_level_groups = [created_group]
            except Exception as exc:  # noqa: BLE001
                logger.warning("group creation failed: %s", exc)
                top_level_groups = top_nodes[:]
        else:
            top_level_groups = top_nodes[:]

        # ------------------------------------------------------------------
        # Post-import transforms
        # ------------------------------------------------------------------
        _apply_axis_conversion(cmds, top_nodes, resolved_axis_conversion)
        _apply_unit_scale(cmds, top_nodes, resolved_unit_scale)

        # ------------------------------------------------------------------
        # Material mode
        # ------------------------------------------------------------------
        _apply_material_mode(cmds, new_long, material_mode)

        # ------------------------------------------------------------------
        # Placement hint
        # ------------------------------------------------------------------
        _apply_placement_hint(cmds, top_nodes, placement_hint, custom_position)

        # ------------------------------------------------------------------
        # Target collection
        # ------------------------------------------------------------------
        if target_collection:
            _apply_target_collection(cmds, top_nodes, target_collection)

        # ------------------------------------------------------------------
        # Build result
        # ------------------------------------------------------------------
        result: Dict[str, Any] = {
            "asset_id": asset.get("id", ""),
            "asset_name": asset.get("name", os.path.splitext(os.path.basename(normalized))[0]),
            "path": normalized,
            "format": fmt,
            "imported_short_names": new_short,
            "imported_long_names": new_long,
            "top_level_groups": top_level_groups,
            "size_bytes": os.path.getsize(normalized),
            "axis_conversion": resolved_axis_conversion,
            "unit_scale": resolved_unit_scale,
            "material_mode": material_mode,
            "placement_hint": placement_hint,
            "target_collection": target_collection,
            "source_unit": semantics["source_unit"],
            "source_up_axis": semantics["source_up_axis"],
            "target_unit": semantics["target_unit"],
            "target_up_axis": semantics["target_up_axis"],
            "unit_conversion_factor": semantics["unit_factor"],
            "warnings": semantics["warnings"],
        }

        message = "Imported '{}' ({} node(s))".format(result["asset_name"], len(new_short))
        if result["warnings"]:
            message = "{} -- {}".format(message, " ".join(result["warnings"]))

        return skill_success(
            message,
            **result,
            prompt=(
                "Use maya_scene__get_selection or maya_scene__get_scene_info to "
                "inspect the imported hierarchy. top_level_groups lists the "
                "world-root transforms. Check the 'warnings' field: when source "
                "semantics were undeclared it records the assumption that was applied."
            ),
        )

    except ImportError:
        return skill_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Failed to import asset to scene")


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; delegates to :func:`import_to_scene`."""
    return import_to_scene(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
