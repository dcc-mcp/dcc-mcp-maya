"""Maya adapter for immutable dcc-mcp-core Asset Sync revisions."""

from __future__ import annotations

import os
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from dcc_mcp_core.skill import skill_error, skill_exception, skill_success

_USD_FORMATS = {
    "usd": "model/vnd.usd",
    "usda": "model/vnd.usda",
    "usdc": "model/vnd.usdc",
    "usdz": "model/vnd.usdz+zip",
}

_IMAGE_TEXTURE_PATH_ATTRS = {"file": "fileTextureName", "aiImage": "filename"}
_IMAGE_TEXTURE_EVIDENCE_LIMIT = 256
_TEXTURE_GRAPH_DEPTH_LIMIT = 8
_TEXTURE_GRAPH_NODE_LIMIT = 512
_TEXTURE_MATERIAL_INPUT_LIMIT = 64
_NON_SHADING_GRAPH_TYPES = {
    "defaultTextureList",
    "displayLayer",
    "objectSet",
    "renderLayer",
    "shadingEngine",
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


@contextmanager
def _maya_namespace(cmds: Any, namespace: Optional[str]):
    """Import into a Maya namespace without relying on an importer flag.

    ``mayaUSDImport`` in Maya 2026 does not expose a ``namespace`` command
    flag.  Maya's current namespace is the supported host-level contract and
    applies consistently to both native USD imports and proxy creation.
    """
    if not namespace:
        yield
        return
    previous = cmds.namespaceInfo(currentNamespace=True)
    if not cmds.namespace(exists=namespace):
        cmds.namespace(add=namespace)
    try:
        cmds.namespace(set=namespace)
        yield
    finally:
        cmds.namespace(set=previous)


def _get_attr(cmds: Any, plug: str) -> Any:
    try:
        return cmds.getAttr(plug)
    except Exception:
        return None


def _workspace_texture_candidates(cmds: Any, authored_path: str) -> List[Path]:
    """Return deterministic Maya-project candidates without mutating workspace state."""
    if not authored_path:
        return []
    expanded = Path(os.path.expandvars(os.path.expanduser(authored_path)))
    if expanded.is_absolute():
        return [expanded]
    try:
        workspace_root = Path(cmds.workspace(query=True, rootDirectory=True))
    except Exception:
        return [expanded]
    candidates = [workspace_root / expanded]
    try:
        source_images = str(cmds.workspace(fileRuleEntry="sourceImages") or "").strip()
    except Exception:
        source_images = ""
    if source_images:
        source_candidate = workspace_root / source_images / expanded
        if source_candidate not in candidates:
            candidates.append(source_candidate)
    return candidates


def _path_or_sequence_exists(path: Path) -> bool:
    """Handle concrete files plus the common Maya UDIM/sequence tokens."""
    if path.is_file():
        return True
    pattern = str(path)
    replacements = {
        "<UDIM>": "[0-9][0-9][0-9][0-9]",
        "<udim>": "[0-9][0-9][0-9][0-9]",
        "<UVTILE>": "u*_v*",
        "<uvtile>": "u*_v*",
        "####": "[0-9][0-9][0-9][0-9]",
    }
    matched_token = False
    for token, replacement in replacements.items():
        if token in pattern:
            pattern = pattern.replace(token, replacement)
            matched_token = True
    if not matched_token:
        return False
    return any(Path(item).is_file() for item in path.parent.glob(Path(pattern).name))


def _connection_pairs(cmds: Any, node: str) -> Iterable[Tuple[str, str]]:
    """Yield normalized ``(node output, downstream input)`` pairs."""
    try:
        raw = (
            cmds.listConnections(
                node,
                source=False,
                destination=True,
                plugs=True,
                connections=True,
            )
            or []
        )
    except Exception:
        return
    prefix = node + "."
    for index in range(0, len(raw) - 1, 2):
        left, right = str(raw[index]), str(raw[index + 1])
        if left.startswith(prefix):
            yield left, right
        elif right.startswith(prefix):
            yield right, left


def _is_traversable_shading_node(cmds: Any, node: str) -> bool:
    try:
        if cmds.nodeType(node) in _NON_SHADING_GRAPH_TYPES:
            return False
    except Exception:
        return False
    try:
        if cmds.objectType(node, isAType="dagNode"):
            return False
    except Exception:
        pass
    return True


def _connected_material_inputs(
    cmds: Any,
    texture: str,
    materials: Set[str],
    imported_nodes: Set[str],
) -> Tuple[List[Dict[str, Any]], bool]:
    """Trace a bounded downstream shading graph to material input plugs."""
    queue = deque([(texture, tuple(), 0)])
    visited = {texture}
    found: Dict[Tuple[str, str], Dict[str, Any]] = {}
    traversal_truncated = False
    while queue:
        current, via, depth = queue.popleft()
        for source_plug, destination_plug in _connection_pairs(cmds, current):
            source_attr = source_plug.split(".", 1)[-1]
            destination_node, separator, destination_attr = destination_plug.partition(".")
            if not separator or source_attr == "message" or destination_attr == "message":
                continue
            if destination_node in materials:
                key = (destination_node, destination_attr)
                found[key] = {
                    "material": destination_node,
                    "input": destination_attr,
                    "plug": destination_plug,
                    "direct": not via,
                    "via": list(via),
                    "material_imported": destination_node in imported_nodes,
                }
                if len(found) >= _TEXTURE_MATERIAL_INPUT_LIMIT:
                    traversal_truncated = True
                    queue.clear()
                    break
                continue
            if depth >= _TEXTURE_GRAPH_DEPTH_LIMIT or destination_node in visited:
                continue
            if not _is_traversable_shading_node(cmds, destination_node):
                continue
            if len(visited) >= _TEXTURE_GRAPH_NODE_LIMIT:
                traversal_truncated = True
                queue.clear()
                break
            visited.add(destination_node)
            queue.append((destination_node, via + (destination_node,), depth + 1))
    ordered = [found[key] for key in sorted(found)]
    return ordered, traversal_truncated


def _image_texture_evidence(cmds: Any, textures: Iterable[str], new_set: Set[str]) -> Dict[str, Any]:
    """Collect bounded, path-aware evidence for Maya and Arnold image nodes."""
    texture_nodes = sorted(set(textures), key=lambda node: (node not in new_set, node))
    selected = texture_nodes[:_IMAGE_TEXTURE_EVIDENCE_LIMIT]
    materials = set(cmds.ls(materials=True) or [])
    records = []
    for texture in selected:
        node_type = cmds.nodeType(texture)
        path_attr = _IMAGE_TEXTURE_PATH_ATTRS[node_type]
        raw_path = _get_attr(cmds, texture + "." + path_attr)
        path = str(raw_path or "")
        expanded = os.path.expandvars(os.path.expanduser(path))
        candidates = _workspace_texture_candidates(cmds, path)
        exists = any(_path_or_sequence_exists(candidate) for candidate in candidates)
        workspace_relative_path = None
        try:
            workspace_root = Path(cmds.workspace(query=True, rootDirectory=True)).resolve()
        except Exception:
            workspace_root = None
        if workspace_root is not None:
            for candidate in candidates:
                try:
                    relative = candidate.resolve().relative_to(workspace_root)
                except (OSError, ValueError):
                    continue
                # Prefer the project-relative spelling that resolves to an
                # existing concrete file or tokenized sequence. Maya commonly
                # expands a portable project path to an absolute getAttr value
                # when a scene is opened, so string absoluteness alone is not
                # sufficient portability evidence.
                workspace_relative_path = relative.as_posix()
                if _path_or_sequence_exists(candidate):
                    break
        color_space = _get_attr(cmds, texture + ".colorSpace")
        if color_space is None:
            color_space = _get_attr(cmds, texture + ".color_space")
        connected_inputs, connections_truncated = _connected_material_inputs(
            cmds,
            texture,
            materials,
            new_set,
        )
        records.append(
            {
                "node": texture,
                "type": node_type,
                "path": path,
                "path_attr": path_attr,
                "exists": exists,
                "color_space": color_space,
                "is_absolute": Path(expanded).is_absolute() if expanded else False,
                "workspace_relative_path": workspace_relative_path,
                "under_workspace": workspace_relative_path is not None,
                "imported": texture in new_set,
                "connected_material_inputs": connected_inputs,
                "connections_truncated": connections_truncated,
            }
        )
    return {
        "records": records,
        "total": len(texture_nodes),
        "limit": _IMAGE_TEXTURE_EVIDENCE_LIMIT,
        "truncated": len(texture_nodes) > len(selected),
    }


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

    textures = (cmds.ls(type="file") or []) + (cmds.ls(type="aiImage") or [])
    texture_evidence = _image_texture_evidence(cmds, textures, new_set)
    missing = []
    for texture in textures:
        try:
            path_attr = "fileTextureName" if cmds.nodeType(texture) == "file" else "filename"
            path = cmds.getAttr(texture + "." + path_attr)
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
    pbr_materials = []
    for material in cmds.ls(materials=True) or []:
        if material not in new_set or cmds.nodeType(material) != "standardSurface":
            continue
        connection_pairs = (
            cmds.listConnections(material, source=True, destination=False, plugs=True, connections=True) or []
        )
        connected_inputs = sorted(
            {
                connection_pairs[index].rsplit(".", 1)[-1]
                for index in range(0, len(connection_pairs) - 1, 2)
                if connection_pairs[index].startswith(material + ".")
            }
        )
        pbr_materials.append(
            {
                "name": material,
                "model": "Arnold standardSurface",
                "metalness": float(cmds.getAttr(material + ".metalness")),
                "specular_roughness": float(cmds.getAttr(material + ".specularRoughness")),
                "specular_ior": float(cmds.getAttr(material + ".specularIOR")),
                "transmission": float(cmds.getAttr(material + ".transmission")),
                "coat": float(cmds.getAttr(material + ".coat")),
                "connected_inputs": connected_inputs,
            }
        )
    return {
        "nodes": len(new_nodes),
        "transforms": count_type("transform"),
        "joints": count_type("joint"),
        "skin_clusters": count_type("skinCluster"),
        "anim_curves": sum(count_type(t) for t in ("animCurveTA", "animCurveTL", "animCurveTT", "animCurveTU")),
        "nurbs_curves": count_type("nurbsCurve"),
        "materials": len(cmds.ls(materials=True) or []),
        "arnold_standard_surface_materials": len(pbr_materials),
        "pbr_materials": pbr_materials,
        "file_textures": len(textures),
        "missing_textures": missing,
        "image_textures": texture_evidence["records"],
        "image_texture_evidence_total": texture_evidence["total"],
        "image_texture_evidence_limit": texture_evidence["limit"],
        "image_texture_evidence_truncated": texture_evidence["truncated"],
        "world_bbox": bbox,
    }


def _usd_rig_evidence(path: Path) -> Dict[str, int]:
    """Read standard USD rig schemas before mutating the Maya scene."""
    from pxr import Usd, UsdGeom, UsdSkel

    stage = Usd.Stage.Open(str(path))
    if not stage:
        raise ValueError("Materialized USD revision could not be opened")
    skeletons = 0
    animations = 0
    skinned_prims = 0
    for prim in stage.Traverse():
        if prim.IsA(UsdSkel.Skeleton):
            skeletons += 1
        elif prim.IsA(UsdSkel.Animation):
            animations += 1
        if (
            prim.IsA(UsdGeom.Mesh)
            and prim.HasAttribute("primvars:skel:jointIndices")
            and prim.HasAttribute("primvars:skel:jointWeights")
        ):
            skinned_prims += 1
    return {"skeletons": skeletons, "animations": animations, "skinned_prims": skinned_prims}


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
    rig_expectation: str = "auto",
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
        source_rig = _usd_rig_evidence(path)
        if rig_expectation in ("skeleton", "skinned") and not source_rig["skeletons"]:
            return skill_error(
                "USD revision has no standard skeleton",
                "The requested rig contract requires UsdSkelSkeleton before Maya import",
                source_rig=source_rig,
            )
        if rig_expectation == "skinned" and not source_rig["skinned_prims"]:
            return skill_error(
                "USD revision has no skin bindings",
                "The requested rig contract requires joint indices and weights before Maya import",
                source_rig=source_rig,
            )
        _ensure_plugin(cmds, "mayaUsdPlugin")
        before = set(cmds.ls(long=True) or [])
        with _maya_namespace(cmds, namespace):
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
                timeline = head.metadata.get("timeline", {})
                if read_animation and "start" in timeline and "end" in timeline:
                    kwargs["frameRange"] = (timeline["start"], timeline["end"])
                cmds.mayaUSDImport(**kwargs)
        after = set(cmds.ls(long=True) or [])
        new_nodes = sorted(after - before)
        evidence = _scene_evidence(cmds, new_nodes)
        evidence["source_rig"] = source_rig
        require_skeleton = rig_expectation in ("skeleton", "skinned") or (
            rig_expectation == "auto" and source_rig["skeletons"] > 0
        )
        if editability_mode == "native" and require_skeleton and evidence["joints"] == 0:
            return skill_error(
                "Maya did not preserve the USD skeleton",
                "The revision contains UsdSkel data but native import produced no Maya joints",
                evidence=evidence,
            )
        if editability_mode == "native" and rig_expectation == "skinned" and evidence["skin_clusters"] == 0:
            return skill_error(
                "Maya did not preserve skin deformation",
                "The revision contains skin bindings but native import produced no skinCluster nodes",
                evidence=evidence,
            )
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
