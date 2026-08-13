"""Maya adapter for immutable dcc-mcp-core Asset Sync revisions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

_USD_FORMATS = {
    "usd": "model/vnd.usd",
    "usda": "model/vnd.usda",
    "usdc": "model/vnd.usdc",
    "usdz": "model/vnd.usdz+zip",
}


def _core_types() -> Tuple[Any, Any, Any]:
    try:
        from dcc_mcp_core.asset_sync import AssetSyncConflictError, AssetSyncValidationError, FileAssetSyncStore
    except ImportError as exc:
        raise RuntimeError(
            "This runtime does not include dcc_mcp_core.asset_sync; install a Core build containing Asset Sync"
        ) from exc
    return FileAssetSyncStore, AssetSyncConflictError, AssetSyncValidationError


def _configured_root(name: str) -> Path:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError("{} is not configured".format(name))
    return Path(value).expanduser().resolve()


def _safe_relative(root: Path, value: str) -> Path:
    relative = Path(str(value).replace("\\", "/"))
    if relative.is_absolute() or not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise ValueError("source_name must be a safe relative path")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("source_name escapes the configured source root") from exc
    return resolved


def publish_usd_revision(
    channel_id: str,
    asset_id: str,
    source_name: str,
    expected_head_revision: int,
    source_instance_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        source = _safe_relative(_configured_root("DCC_MCP_MAYA_ASSET_SYNC_SOURCE_ROOT"), source_name)
        extension = source.suffix.lower().lstrip(".")
        if extension not in _USD_FORMATS:
            raise ValueError("Asset Sync accepts only USD, USDA, USDC, or USDZ")
        if not source.is_file():
            raise FileNotFoundError(str(source))
        Store, _, _ = _core_types()
        revision = Store(_configured_root("DCC_MCP_ASSET_SYNC_ROOT")).publish(
            source,
            channel_id=channel_id,
            asset_id=asset_id,
            format=extension,
            mime=_USD_FORMATS[extension],
            expected_head_revision=expected_head_revision,
            source_instance_id=source_instance_id or os.environ.get("DCC_MCP_INSTANCE_ID"),
            metadata=dict(metadata or {}),
        )
        return skill_success("Published Asset Sync revision {}".format(revision.revision), revision=revision.to_dict())
    except Exception as exc:
        return skill_exception(exc, message="Failed to publish USD revision")


def read_asset_head(channel_id: str, asset_id: str) -> Dict[str, Any]:
    try:
        Store, _, _ = _core_types()
        head = Store(_configured_root("DCC_MCP_ASSET_SYNC_ROOT")).read_head(channel_id, asset_id)
        if head is None:
            return skill_error("Asset has not been published", "No head exists for the requested channel and asset")
        return skill_success("Asset Sync head is revision {}".format(head.revision), revision=head.to_dict())
    except Exception as exc:
        return skill_exception(exc, message="Failed to read Asset Sync head")


def _ensure_plugin(cmds: Any, name: str) -> None:
    if not cmds.pluginInfo(name, query=True, loaded=True):
        cmds.loadPlugin(name)


def _scene_evidence(cmds: Any, new_nodes: Any) -> Dict[str, Any]:
    new_set = set(new_nodes)

    def count_type(node_type: str) -> int:
        return len(
            [
                node
                for node in (cmds.ls(type=node_type, long=True) or [])
                if node in new_set or any(node.startswith(parent + "|") for parent in new_set)
            ]
        )

    textures = cmds.ls(type="file") or []
    missing = []
    for texture in textures:
        try:
            path = cmds.getAttr(texture + ".fileTextureName")
            if path and not Path(path).is_file():
                missing.append(texture)
        except Exception:
            pass
    bbox = None
    dag = [node for node in new_nodes if cmds.objExists(node)]
    if dag:
        try:
            bbox = [float(value) for value in cmds.exactWorldBoundingBox(dag)]
        except Exception:
            pass
    return {
        "nodes": len(new_nodes),
        "transforms": count_type("transform"),
        "joints": count_type("joint"),
        "anim_curves": sum(count_type(t) for t in ("animCurveTA", "animCurveTL", "animCurveTT", "animCurveTU")),
        "nurbs_curves": count_type("nurbsCurve"),
        "materials": len(cmds.ls(materials=True) or []),
        "file_textures": len(textures),
        "missing_textures": missing,
        "world_bbox": bbox,
    }


def sync_usd_revision(
    channel_id: str,
    asset_id: str,
    editability_mode: str = "native",
    namespace: Optional[str] = None,
    subfolder: str = "",
    read_animation: bool = True,
    apply_euler_filter: bool = True,
    preserve_materials: bool = True,
    axis_and_unit_method: str = "addTransform",
) -> Dict[str, Any]:
    try:
        from maya import cmds

        Store, _, _ = _core_types()
        store = Store(_configured_root("DCC_MCP_ASSET_SYNC_ROOT"))
        head = store.read_head(channel_id, asset_id)
        if head is None:
            return skill_error("Asset has not been published", "No head exists for the requested channel and asset")
        if head.format not in _USD_FORMATS:
            return skill_error("Unsupported revision format", "Maya Asset Sync currently requires USD")
        path = store.materialize(head, _configured_root("DCC_MCP_MAYA_ASSET_SYNC_CONSUMER_ROOT"), subfolder=subfolder)
        _ensure_plugin(cmds, "mayaUsdPlugin")
        before = set(cmds.ls(long=True) or [])
        if editability_mode == "usd_proxy":
            transform = cmds.createNode("transform", name="{}_USD_SYNC".format(asset_id.replace("-", "_")))
            shape = cmds.createNode("mayaUsdProxyShape", parent=transform, name=transform + "Shape")
            cmds.setAttr(shape + ".filePath", str(path).replace("\\", "/"), type="string")
        else:
            kwargs = {
                "file": str(path).replace("\\", "/"),
                "primPath": "/",
                "readAnimData": read_animation,
                "applyEulerFilter": apply_euler_filter,
                "upAxis": True,
                "unit": True,
                "axisAndUnitMethod": axis_and_unit_method,
                "shadingMode": [["useRegistry", "UsdPreviewSurface"]]
                if preserve_materials
                else [["none", "defaultMaterial"]],
                "preferredMaterial": "standardSurface",
            }
            if namespace:
                kwargs["namespace"] = namespace
            timeline = head.metadata.get("timeline", {})
            if read_animation and "start" in timeline and "end" in timeline:
                kwargs["frameRange"] = (timeline["start"], timeline["end"])
            cmds.mayaUSDImport(**kwargs)
        after = set(cmds.ls(long=True) or [])
        new_nodes = sorted(after - before)
        evidence = _scene_evidence(cmds, new_nodes)
        metadata_node = cmds.createNode("network", name="DCC_MCP_ASSET_SYNC_METADATA")
        for attr, value in (
            ("channelId", channel_id),
            ("assetId", asset_id),
            ("digest", head.digest),
            ("editabilityMode", editability_mode),
        ):
            cmds.addAttr(metadata_node, longName=attr, dataType="string")
            cmds.setAttr(metadata_node + "." + attr, value, type="string")
        cmds.addAttr(metadata_node, longName="revision", attributeType="long")
        cmds.setAttr(metadata_node + ".revision", head.revision)
        editable = [node for node in new_nodes if cmds.objExists(node) and cmds.objectType(node, isAType="dagNode")]
        set_name = None
        if editability_mode == "native" and editable:
            set_name = cmds.sets(editable, name="{}_EDITABLE_SYNC_SET".format(asset_id.replace("-", "_")))
        return skill_success(
            "Synchronized Asset Sync revision {} in {} mode".format(head.revision, editability_mode),
            revision=head.to_dict(),
            materialized_name=path.name,
            editability_mode=editability_mode,
            editable_set=set_name,
            evidence=evidence,
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to synchronize USD revision")
