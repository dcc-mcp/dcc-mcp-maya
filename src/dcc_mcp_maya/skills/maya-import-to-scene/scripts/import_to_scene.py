"""Import an asset into the current Maya scene using typed AssetDescriptor contracts.

This is the contract-shaped counterpart to the low-level import tools in
maya-geometry.  It accepts a structured ImportToSceneRequest, dispatches
to the appropriate format importer, applies material mode and placement
hints, and returns ImportToSceneResult.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from typing import Any, Dict, List, Optional

# Import local modules
from dcc_mcp_core.asset_import import (
    AssetDescriptor,
    AssetFileVariant,
    AssetFormat,
    ImportToSceneRequest,
    ImportToSceneResult,
    ImportWarning,
    PlacementHint,
)
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

logger = logging.getLogger(__name__)

# Normalized extension -> AssetFormat mapping.
_EXTENSION_TO_FORMAT = {
    ".fbx": AssetFormat.FBX,
    ".obj": AssetFormat.OBJ,
    ".usd": AssetFormat.USD,
    ".usda": AssetFormat.USD,
    ".usdc": AssetFormat.USD,
    ".usdz": AssetFormat.USDZ,
    ".gltf": AssetFormat.GLTF,
    ".glb": AssetFormat.GLB,
    ".abc": AssetFormat.ABC,
}

# Plug-in names keyed by AssetFormat.
_FORMAT_PLUGINS = {
    AssetFormat.FBX: ("fbxmaya",),
    AssetFormat.OBJ: ("objExport",),
    AssetFormat.USD: ("mayaUsdPlugin",),
    AssetFormat.USDZ: ("mayaUsdPlugin",),
    AssetFormat.GLTF: ("glTFPlugin",),
    AssetFormat.GLB: ("glTFPlugin",),
    AssetFormat.ABC: ("AbcImport",),
}

# Priority ranking for format selection (lower = better).
_FORMAT_PRIORITY = {
    AssetFormat.FBX: 0,
    AssetFormat.OBJ: 1,
    AssetFormat.USD: 2,
    AssetFormat.USDZ: 3,
    AssetFormat.GLTF: 4,
    AssetFormat.GLB: 5,
    AssetFormat.ABC: 6,
}


def _normalize_path(path: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded.replace("\\", "/")


def _ensure_plugins(cmds: Any, format_: AssetFormat) -> List[str]:
    """Load the required Maya plug-in(s) for *format_*."""
    plugin_names = _FORMAT_PLUGINS.get(format_, ())
    loaded = []
    for plugin_name in plugin_names:
        if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
            cmds.loadPlugin(plugin_name)
            loaded.append(plugin_name)
    return loaded


def _detect_format(path: str) -> AssetFormat:
    """Detect AssetFormat from file extension."""
    ext = os.path.splitext(path)[1].lower()
    return _EXTENSION_TO_FORMAT.get(ext, AssetFormat.UNKNOWN)


def _select_best_variant(descriptor: AssetDescriptor) -> AssetFileVariant:
    """Select the best file variant for Maya import.

    Priority: preferred flag > format priority (FBX best) > first match.
    """
    if not descriptor.variants:
        msg = "No variants in AssetDescriptor"
        raise ValueError(msg)

    # First pass: prefer explicitly preferred variants.
    preferred = [v for v in descriptor.variants if v.preferred]
    if preferred:
        return preferred[0]

    # Second pass: pick by format priority (FBX > OBJ > USD > GLTF > ABC).
    scored = [(v, _FORMAT_PRIORITY.get(_detect_format(v.local_path), 99)) for v in descriptor.variants]
    scored.sort(key=lambda pair: pair[1])
    return scored[0][0]


def _check_skip_existing(cmds: Any, descriptor: AssetDescriptor) -> Optional[str]:
    """Return the existing root node name if skip_existing matches."""
    if not descriptor.asset_id:
        return None
    for node in cmds.ls(type="transform") or []:
        if cmds.attributeQuery("dcc_mcp_asset_id", node=node, exists=True):
            stored = cmds.getAttr("{}.dcc_mcp_asset_id".format(node))
            if stored == descriptor.asset_id:
                return node
    return None


def _tag_asset_id(cmds: Any, node: str, asset_id: str) -> None:
    """Tag *node* with the *asset_id* attribute for skip-existing dedup."""
    if not asset_id:
        return
    if not cmds.attributeQuery("dcc_mcp_asset_id", node=node, exists=True):
        cmds.addAttr(node, longName="dcc_mcp_asset_id", dataType="string")
    cmds.setAttr("{}.dcc_mcp_asset_id".format(node), asset_id, type="string")


def _get_imported_nodes(
    cmds: Any,
    format_: AssetFormat,
) -> List[str]:
    """Return the list of newly imported node names."""
    if format_ == AssetFormat.FBX:
        return cmds.ls(long=True) or []
    return cmds.ls(importedNodes=True, long=True) or []


def _apply_placement(
    cmds: Any,
    imported_nodes: List[str],
    placement: Optional[PlacementHint],
) -> None:
    """Apply placement transform to the imported top-level root(s)."""
    if not placement:
        return

    # Find top-level transforms among imported nodes.
    tops = [n for n in imported_nodes if n.count("|") <= 1 and cmds.objectType(n) == "transform"]
    if not tops:
        return

    root = tops[0]

    if placement.parent_name:
        try:
            parent = placement.parent_name
            if not cmds.objExists(parent):
                logger.warning("Placement parent %s not found, skipping", parent)
            else:
                cmds.parent(root, parent)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to parent %s to %s", root, placement.parent_name)

    if any(v is not None for v in [placement.translate, placement.rotate, placement.scale]):
        tx, ty, tz = placement.translate or [0.0, 0.0, 0.0]
        rx, ry, rz = placement.rotate or [0.0, 0.0, 0.0]
        sx, sy, sz = placement.scale or [1.0, 1.0, 1.0]
        cmds.setAttr("{}.translate".format(root), tx, ty, tz, type="double3")
        cmds.setAttr("{}.rotate".format(root), rx, ry, rz, type="double3")
        cmds.setAttr("{}.scale".format(root), sx, sy, sz, type="double3")


def _apply_material_mode(
    cmds: Any,
    material_mode: str,
) -> List[ImportWarning]:
    """Apply material mode after import.

    Returns a list of warnings for non-fatal material issues.
    """
    warnings: List[ImportWarning] = []

    if material_mode == "skip":
        # Delete all shading engines and materials.
        try:
            shading_groups = cmds.ls(type="shadingEngine") or []
            for sg in shading_groups:
                if sg != "initialShadingGroup":
                    cmds.delete(sg)
            materials = cmds.ls(mat=True) or []
            for mat in materials:
                if mat not in ("lambert1", "standardSurface1", "particleCloud1"):
                    cmds.delete(mat)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                ImportWarning(
                    code="MATERIAL_SKIP_FAILED",
                    message="Failed to strip materials: {}".format(exc),
                )
            )
    elif material_mode == "default_gray":
        # Assign lambert1 to all mesh faces.
        try:
            meshes = cmds.ls(type="mesh") or []
            if meshes:
                cmds.hyperShade(assign="lambert1")
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                ImportWarning(
                    code="MATERIAL_GRAY_FAILED",
                    message="Failed to assign default gray: {}".format(exc),
                )
            )

    return warnings


def _assign_to_collection(
    cmds: Any,
    imported_nodes: List[str],
    collection_name: str,
) -> None:
    """Assign imported roots to a display layer."""
    if not collection_name:
        return

    # Find or create the display layer.
    layers = cmds.ls(type="displayLayer") or []
    layer = next((lyr for lyr in layers if lyr == collection_name), None)
    if layer is None:
        layer = cmds.createDisplayLayer(name=collection_name, empty=True)

    # Add top-level transforms to the layer.
    tops = [n for n in imported_nodes if n.count("|") <= 1 and cmds.objectType(n) == "transform"]
    if tops:
        cmds.editDisplayLayerMembers(layer, tops, noRecurse=True)


def import_to_scene(request: ImportToSceneRequest) -> Dict[str, Any]:
    """Import an asset into the current Maya scene.

    Args:
        request: Fully populated ImportToSceneRequest.

    Returns:
        ToolResult dict with ImportToSceneResult in ``context``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415
    except ImportError:
        return skill_error(
            "Maya not available",
            "maya.cmds could not be imported",
            possible_solutions=["Run inside Maya or mayapy"],
        )

    descriptor = request.descriptor
    material_mode = request.material_mode or "as_authored"
    placement = request.placement
    collection = request.target_collection
    skip_existing = request.skip_existing
    extra = request.extra or {}

    warnings: List[ImportWarning] = []

    # --- Skip-existing check -------------------------------------------------
    existing_root = _check_skip_existing(cmds, descriptor)
    if skip_existing and existing_root is not None:
        return skill_success(
            "Skipped import: asset_id '{}' already present (node: {})".format(descriptor.asset_id, existing_root),
            result=ImportToSceneResult(
                success=True,
                imported_nodes=[existing_root],
                warnings=[
                    ImportWarning(
                        code="SKIP_EXISTING",
                        message="Already imported as {}".format(existing_root),
                    )
                ],
                error_message=None,
                extra=extra,
            ),
            prompt="Use get_scene_info to inspect the existing asset.",
        )

    # --- Select best variant -------------------------------------------------
    try:
        variant = _select_best_variant(descriptor)
    except ValueError as exc:
        return skill_error(
            "No variants available",
            str(exc),
            asset_id=descriptor.asset_id,
        )

    file_path = _normalize_path(variant.local_path)
    if not os.path.exists(file_path):
        return skill_error(
            "File not found",
            "{} does not exist on disk".format(file_path),
            file_path=file_path,
            asset_id=descriptor.asset_id,
        )

    detected_format = _detect_format(file_path)

    # --- BLEND is unsupported ------------------------------------------------
    ext_lower = os.path.splitext(file_path)[1].lower()
    if ext_lower == ".blend":
        return skill_error(
            "Unsupported format",
            "Blender .blend files cannot be imported into Maya",
            file_path=file_path,
            format="BLEND",
        )

    # --- Load plug-ins -------------------------------------------------------
    if detected_format != AssetFormat.UNKNOWN:
        try:
            _ensure_plugins(cmds, detected_format)
        except Exception as exc:  # noqa: BLE001
            return skill_error(
                "Plugin unavailable",
                "Failed to load plugin for {}: {}".format(file_path, exc),
                file_path=file_path,
                format=str(detected_format),
            )

    # --- Snapshot scene state before import ----------------------------------
    before = cmds.ls(long=True) or []

    # --- Dispatch import by format -------------------------------------------
    try:
        namespace = descriptor.asset_id.replace("/", "_").replace("\\", "_") if descriptor.asset_id else None
        import_kwargs: Dict[str, Any] = {
            "i": True,
            "prompt": False,
        }
        if namespace:
            import_kwargs["namespace"] = namespace

        if detected_format == AssetFormat.FBX:
            from maya import mel  # noqa: PLC0415

            mel.eval("FBXResetImport")
            mel.eval("FBXImportMode -v add")
            if material_mode == "skip":
                mel.eval("FBXImportMaterials -v false")
            else:
                mel.eval("FBXImportMaterials -v true")
            import_kwargs["type"] = "FBX"
            import_kwargs["ignoreVersion"] = True
            import_kwargs["options"] = "fbx"
            import_kwargs["preserveReferences"] = True
            cmds.file(file_path, **import_kwargs)
        elif detected_format in (AssetFormat.USD, AssetFormat.USDZ):
            import_kwargs["type"] = "USD Import"
            import_kwargs["ignoreVersion"] = True
            import_kwargs["preserveReferences"] = True
            cmds.file(file_path, **import_kwargs)
        else:
            # OBJ, GLTF, ABC, UNKNOWN -> generic import_file path.
            cmds.file(file_path, **import_kwargs)

        after = cmds.ls(long=True) or []
    except Exception as exc:  # noqa: BLE001
        return skill_exception(
            exc,
            message="Import failed: {}".format(file_path),
            file_path=file_path,
            asset_id=descriptor.asset_id,
            format=str(detected_format),
        )

    # --- Determine imported nodes --------------------------------------------
    before_set = set(before)
    imported_long = [n for n in after if n not in before_set]

    if not imported_long:
        # Fallback: mayaUsd may not report in ls diff.
        try:
            imported_long = cmds.ls(importedNodes=True, long=True) or []
        except Exception:  # noqa: BLE001
            imported_long = []

    # --- Tag asset_id on the first transform ---------------------------------
    if descriptor.asset_id:
        roots = [n for n in imported_long if n.count("|") <= 1 and cmds.objectType(n) == "transform"]
        if roots:
            _tag_asset_id(cmds, roots[0], descriptor.asset_id)

    # --- Apply placement -----------------------------------------------------
    try:
        _apply_placement(cmds, imported_long, placement)
    except Exception as exc:  # noqa: BLE001
        warnings.append(
            ImportWarning(
                code="PLACEMENT_FAILED",
                message="Placement hint partially failed: {}".format(exc),
            )
        )

    # --- Apply material mode -------------------------------------------------
    if material_mode != "as_authored":
        mat_warnings = _apply_material_mode(cmds, material_mode)
        warnings.extend(mat_warnings)

    # --- Assign to collection / display layer ---------------------------------
    if collection:
        try:
            _assign_to_collection(cmds, imported_long, collection)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                ImportWarning(
                    code="COLLECTION_FAILED",
                    message="Failed to assign to layer '{}': {}".format(collection, exc),
                )
            )

    result = ImportToSceneResult(
        success=True,
        imported_nodes=imported_long,
        warnings=warnings,
        error_message=None,
        extra={
            **(extra or {}),
            "file_path": file_path,
            "asset_id": descriptor.asset_id,
            "namespace": namespace,
            "imported_count": len(imported_long),
        },
    )

    return skill_success(
        "Imported {} node(s) from {}".format(len(imported_long), file_path),
        result=result,
        prompt="Use get_scene_info or get_selection to inspect imported nodes.",
    )


@skill_entry
def main(**kwargs: Any) -> Dict[str, Any]:
    """Entry point; builds ImportToSceneRequest from flat kwargs."""
    try:
        descriptor_kwargs = kwargs.get("descriptor", {})
        if not descriptor_kwargs:
            return skill_error(
                "Missing descriptor",
                "descriptor is required",
                possible_solutions=["Pass an AssetDescriptor with at least one variant"],
            )

        # Convert nested variant dicts to AssetFileVariant objects.
        raw_variants = descriptor_kwargs.get("variants", [])
        variants = []
        for v in raw_variants:
            if isinstance(v, dict):
                variants.append(AssetFileVariant(**v))
            else:
                variants.append(v)
        descriptor_kwargs["variants"] = variants

        # Ensure required descriptor fields have defaults.
        descriptor_kwargs.setdefault("extra", {})
        descriptor = AssetDescriptor(**descriptor_kwargs)

        placement_kwargs = kwargs.get("placement")
        placement = PlacementHint(**placement_kwargs) if placement_kwargs else None

        request = ImportToSceneRequest(
            descriptor=descriptor,
            material_mode=kwargs.get("material_mode", "as_authored"),
            placement=placement,
            target_collection=kwargs.get("target_collection"),
            skip_existing=kwargs.get("skip_existing", False),
            extra=kwargs.get("extra", {}),
        )
        return import_to_scene(request)
    except Exception as exc:
        return skill_exception(exc, message="Failed to build import request")


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
