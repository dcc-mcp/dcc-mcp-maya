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
        selection = cmds.ls(selection=1) or []
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
        # Snapshot scene before import
        # ------------------------------------------------------------------
        before = cmds.ls(long=1) or []

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
            if not merge_namespaces:
                import_kwargs["renamingPrefix"] = namespace

        try:
            cmds.file(normalized, **import_kwargs)
        except RuntimeError as exc:
            return skill_exception(exc, message="cmds.file import raised", path=normalized, format=fmt)

        # ------------------------------------------------------------------
        # Compute new nodes
        # ------------------------------------------------------------------
        after = cmds.ls(long=1) or []
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
        _apply_axis_conversion(cmds, top_nodes, axis_conversion)
        _apply_unit_scale(cmds, top_nodes, unit_scale)

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
            "axis_conversion": axis_conversion,
            "unit_scale": unit_scale,
            "material_mode": material_mode,
            "placement_hint": placement_hint,
            "target_collection": target_collection,
        }

        return skill_success(
            "Imported '{}' ({} node(s))".format(result["asset_name"], len(new_short)),
            **result,
            prompt=(
                "Use maya_scene__get_selection or maya_scene__get_scene_info to "
                "inspect the imported hierarchy. top_level_groups lists the "
                "world-root transforms."
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
