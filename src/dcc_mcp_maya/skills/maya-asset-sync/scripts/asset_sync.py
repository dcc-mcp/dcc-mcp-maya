"""Maya adapter for immutable dcc-mcp-core Asset Sync revisions."""

from __future__ import annotations

import os
import re
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

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
_CONTROLLER_ROLE_ATTR = "dccMcpControllerRole"
_CONTROLLER_EVIDENCE_LIMIT = 128
_CONSTRAINT_EVIDENCE_LIMIT = 256
_CONSTRAINT_TYPES = (
    "parentConstraint",
    "pointConstraint",
    "orientConstraint",
    "scaleConstraint",
    "aimConstraint",
    "poleVectorConstraint",
)
_CONTROLLER_CHANNELS = (
    "translateX",
    "translateY",
    "translateZ",
    "rotateX",
    "rotateY",
    "rotateZ",
    "scaleX",
    "scaleY",
    "scaleZ",
)
_CONTROLLER_ROLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
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


def _in_import_scope(node: str, new_set: Set[str]) -> bool:
    return node in new_set or any(node.startswith(parent + "|") for parent in new_set)


def _long_name(cmds: Any, node: str) -> str:
    try:
        matches = cmds.ls(node, long=True) or []
    except Exception:
        return str(node)
    # A short DAG name may resolve to multiple nodes.  Keeping the authored
    # name in that case deliberately prevents an ambiguous controller match.
    return str(matches[0]) if len(matches) == 1 else str(node)


def _attribute_exists(cmds: Any, node: str, attribute: str) -> bool:
    try:
        return bool(cmds.attributeQuery(attribute, node=node, exists=True))
    except Exception:
        try:
            return bool(cmds.objExists(node + "." + attribute))
        except Exception:
            return False


def _attribute_flag(cmds: Any, plug: str, flag: str) -> Optional[bool]:
    try:
        return bool(cmds.getAttr(plug, **{flag: True}))
    except Exception:
        return None


def _normalize_required_controller_roles(roles: Optional[Sequence[str]]) -> List[str]:
    if roles is None:
        return []
    if isinstance(roles, (str, bytes)):
        raise ValueError("required_constrained_controller_roles must be an array")
    if len(roles) > 64:
        raise ValueError("required_constrained_controller_roles accepts at most 64 roles")
    normalized = []
    seen = set()
    for raw_role in roles:
        if not isinstance(raw_role, str):
            raise ValueError("controller roles must be strings")
        role = raw_role.strip()
        if not _CONTROLLER_ROLE_PATTERN.fullmatch(role):
            raise ValueError("controller roles must use bounded identifier syntax")
        if role in seen:
            raise ValueError("required_constrained_controller_roles must be unique")
        seen.add(role)
        normalized.append(role)
    return sorted(normalized)


def _constraint_query(cmds: Any, node_type: str, node: str, flag: str) -> List[str]:
    command = getattr(cmds, node_type, None)
    if command is None:
        return []
    try:
        return [str(value) for value in (command(node, query=True, **{flag: True}) or [])]
    except Exception:
        return []


def _constraint_record(
    cmds: Any,
    node: str,
    node_type: str,
    new_set: Set[str],
    target_list: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    ordered_drivers = [
        _long_name(cmds, target)
        for target in (
            list(target_list) if target_list is not None else _constraint_query(cmds, node_type, node, "targetList")
        )
    ]
    drivers = sorted(set(ordered_drivers))
    # Maya guarantees positional correspondence between targetList and
    # weightAliasList.  Preserve that order for pairing; sorting first can
    # assign another target's editability state to the required controller.
    ordered_weight_aliases = _constraint_query(cmds, node_type, node, "weightAliasList")
    weight_aliases = sorted(set(ordered_weight_aliases))
    alias_states = {}
    for alias in ordered_weight_aliases:
        locked = _attribute_flag(cmds, node + "." + alias, "lock")
        raw_weight = _get_attr(cmds, node + "." + alias)
        try:
            weight = float(raw_weight) if raw_weight is not None else None
        except (TypeError, ValueError):
            weight = None
        alias_states[alias] = {"locked": locked, "weight": weight}
    target_weights = []
    for index, driver in enumerate(ordered_drivers):
        alias = ordered_weight_aliases[index] if index < len(ordered_weight_aliases) else None
        state = alias_states.get(alias, {})
        locked = state.get("locked")
        weight = state.get("weight")
        target_weights.append(
            {
                "driver": driver,
                "weight_alias": alias,
                "weight": weight,
                "locked": locked,
                "active": weight is not None and abs(weight) > 1.0e-8,
                "editable": locked is False and weight is not None,
            }
        )
    target_weights.sort(key=lambda record: (record["driver"], record["weight_alias"] or ""))
    locked_weight_aliases = sorted(alias for alias, state in alias_states.items() if state["locked"] is True)
    unknown_weight_aliases = sorted(
        alias for alias, state in alias_states.items() if state["locked"] is None or state["weight"] is None
    )
    try:
        destinations = (
            cmds.listConnections(
                node,
                source=False,
                destination=True,
                plugs=True,
            )
            or []
        )
    except Exception:
        destinations = []
    driven = set()
    for destination in destinations:
        destination_node, separator, destination_attr = str(destination).partition(".")
        if not separator or not destination_attr.startswith(("translate", "rotate", "scale")):
            continue
        driven.add(_long_name(cmds, destination_node))
    return {
        "node": str(node),
        "type": node_type,
        "drivers": drivers,
        "driven": sorted(driven),
        "weight_aliases": weight_aliases,
        "locked_weight_aliases": locked_weight_aliases,
        "unknown_weight_aliases": unknown_weight_aliases,
        "target_weights": target_weights,
        "target_weight_mapping_complete": len(ordered_drivers) == len(ordered_weight_aliases),
        "imported": _in_import_scope(str(node), new_set),
        "editable": bool(drivers and driven and any(record["editable"] for record in target_weights)),
    }


def _rig_editability_evidence(
    cmds: Any,
    new_set: Set[str],
    required_roles: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Collect bounded native controller and constraint graph evidence.

    A NURBS curve count is not controller evidence because a synchronized asset
    may contain groom, guide, or decorative curves. Controllers opt in through
    the explicit ``dccMcpControllerRole`` string tag.
    """
    required = _normalize_required_controller_roles(required_roles)
    required_set = set(required)

    candidates = []
    for node in cmds.ls(type="transform", long=True) or []:
        node_name = str(node)
        if not _in_import_scope(node_name, new_set):
            continue
        if not _attribute_exists(cmds, node_name, _CONTROLLER_ROLE_ATTR):
            continue
        role = str(_get_attr(cmds, node_name + "." + _CONTROLLER_ROLE_ATTR) or "").strip()
        if not _CONTROLLER_ROLE_PATTERN.fullmatch(role):
            continue
        try:
            shapes = sorted(
                str(shape)
                for shape in (
                    cmds.listRelatives(
                        node_name,
                        shapes=True,
                        noIntermediate=True,
                        fullPath=True,
                        type="nurbsCurve",
                    )
                    or []
                )
            )
        except Exception:
            shapes = []
        # Maya constraints inherit from transform and therefore appear in
        # cmds.ls(type="transform").  A role tag alone is not controller
        # evidence; require the promised non-intermediate NURBS shape here.
        if not shapes:
            continue
        candidates.append((role, node_name, shapes))
    candidates.sort(key=lambda item: (item[0], item[1]))
    selected_controllers = []
    selected_controller_keys = set()
    # Reserve one slot for every required role before filling the bounded
    # evidence list.  With <=64 required roles and a 128-record limit, one
    # noisy role cannot hide another required controller.
    for role in required:
        match = next((item for item in candidates if item[0] == role), None)
        if match is not None:
            selected_controllers.append(match)
            selected_controller_keys.add((match[0], match[1]))
    for item in candidates:
        if len(selected_controllers) >= _CONTROLLER_EVIDENCE_LIMIT:
            break
        key = (item[0], item[1])
        if key not in selected_controller_keys:
            selected_controllers.append(item)
            selected_controller_keys.add(key)
    selected_controllers.sort(key=lambda item: (item[0], item[1]))

    required_controller_nodes = {node for role, node, _shapes in candidates if role in required_set}
    constraint_nodes = []
    for node_type in _CONSTRAINT_TYPES:
        for node in cmds.ls(type=node_type, long=True) or []:
            node_name = str(node)
            if not _in_import_scope(node_name, new_set):
                continue
            targets = [
                _long_name(cmds, target) for target in _constraint_query(cmds, node_type, node_name, "targetList")
            ]
            constraint_nodes.append((node_type, node_name, targets))
    constraint_nodes.sort(
        key=lambda item: (
            not any(target in required_controller_nodes for target in item[2]),
            item[0],
            item[1],
        )
    )
    selected_constraints = []
    selected_constraint_keys = set()
    # Round-robin required controllers first.  This keeps the bounded output
    # fair when one controller owns hundreds of constraints.  If the limit is
    # still exhausted before a valid relation is observed, the gate remains
    # conservatively fail-closed and the collection reports truncated=true.
    primary_required_nodes = []
    for role in required:
        matches = sorted(node for candidate_role, node, _shapes in candidates if candidate_role == role)
        if matches:
            primary_required_nodes.append(matches[0])
    grouped_required_constraints = [
        [item for item in constraint_nodes if controller_node in item[2]] for controller_node in primary_required_nodes
    ]
    max_group_size = max((len(group) for group in grouped_required_constraints), default=0)
    for index in range(max_group_size):
        for group in grouped_required_constraints:
            if len(selected_constraints) >= _CONSTRAINT_EVIDENCE_LIMIT:
                break
            if index >= len(group):
                continue
            item = group[index]
            key = (item[0], item[1])
            if key not in selected_constraint_keys:
                selected_constraints.append(item)
                selected_constraint_keys.add(key)
        if len(selected_constraints) >= _CONSTRAINT_EVIDENCE_LIMIT:
            break
    for item in constraint_nodes:
        if len(selected_constraints) >= _CONSTRAINT_EVIDENCE_LIMIT:
            break
        key = (item[0], item[1])
        if key not in selected_constraint_keys:
            selected_constraints.append(item)
            selected_constraint_keys.add(key)
    selected_constraints.sort(key=lambda item: (item[0], item[1]))
    constraint_records = [
        _constraint_record(cmds, node, node_type, new_set, targets) for node_type, node, targets in selected_constraints
    ]

    controller_records = []
    for role, node, shapes in selected_controllers:
        keyable_channels = []
        locked_channels = []
        unknown_channel_states = []
        animated_channels = []
        for channel in _CONTROLLER_CHANNELS:
            if not _attribute_exists(cmds, node, channel):
                continue
            plug = node + "." + channel
            locked = _attribute_flag(cmds, plug, "lock")
            keyable = _attribute_flag(cmds, plug, "keyable")
            if locked is True:
                locked_channels.append(channel)
            elif locked is False and keyable is True:
                keyable_channels.append(channel)
            elif locked is None or keyable is None:
                unknown_channel_states.append(channel)
            try:
                animated = (
                    cmds.listConnections(
                        plug,
                        source=True,
                        destination=False,
                        type="animCurve",
                    )
                    or []
                )
            except Exception:
                animated = []
            if animated:
                animated_channels.append(channel)
        driven_constraints = sorted(
            record["node"]
            for record in constraint_records
            if any(target["driver"] == node for target in record["target_weights"])
        )
        editable_driven_constraints = sorted(
            record["node"]
            for record in constraint_records
            if record["driven"]
            and any(target["driver"] == node and target["editable"] for target in record["target_weights"])
        )
        controller_records.append(
            {
                "node": node,
                "role": role,
                "shapes": shapes,
                "shape_type": "nurbsCurve" if shapes else None,
                "keyable_channels": sorted(keyable_channels),
                "locked_channels": sorted(locked_channels),
                "unknown_channel_states": sorted(unknown_channel_states),
                "animated_channels": sorted(animated_channels),
                "driven_constraints": driven_constraints,
                "editable_driven_constraints": editable_driven_constraints,
                "imported": _in_import_scope(node, new_set),
                "editable": bool(shapes and keyable_channels),
            }
        )

    records_by_role: Dict[str, List[Dict[str, Any]]] = {}
    for record in controller_records:
        records_by_role.setdefault(record["role"], []).append(record)
    candidate_counts_by_role = {
        role: sum(candidate_role == role for candidate_role, _node, _shapes in candidates) for role in required
    }
    missing_roles = sorted(role for role in required if candidate_counts_by_role[role] == 0)
    duplicate_roles = sorted(role for role in required if candidate_counts_by_role[role] > 1)
    non_editable_roles = sorted(
        role
        for role in required
        if records_by_role.get(role) and not all(record["editable"] for record in records_by_role[role])
    )
    unconstrained_roles = sorted(
        role
        for role in required
        if records_by_role.get(role)
        and not all(record["editable_driven_constraints"] for record in records_by_role[role])
    )
    all_required_editable = not (missing_roles or duplicate_roles or non_editable_roles)
    all_required_constrained = all_required_editable and not unconstrained_roles
    return {
        "role_attribute": _CONTROLLER_ROLE_ATTR,
        "controllers": {
            "records": controller_records,
            "total": len(candidates),
            "limit": _CONTROLLER_EVIDENCE_LIMIT,
            "truncated": len(candidates) > len(selected_controllers),
        },
        "constraints": {
            "records": constraint_records,
            "total": len(constraint_nodes),
            "limit": _CONSTRAINT_EVIDENCE_LIMIT,
            "truncated": len(constraint_nodes) > len(selected_constraints),
        },
        "required_roles": required,
        "missing_roles": missing_roles,
        "duplicate_roles": duplicate_roles,
        "non_editable_roles": non_editable_roles,
        "unconstrained_roles": unconstrained_roles,
        "all_required_editable": all_required_editable,
        "all_required_constrained": all_required_constrained,
    }


def _required_controller_failures(rig_editability: Mapping[str, Any]) -> List[str]:
    failures = []
    labels = (
        ("missing_roles", "missing controller roles"),
        ("duplicate_roles", "duplicate controller roles"),
        ("non_editable_roles", "non-editable controller roles"),
        ("unconstrained_roles", "unconstrained controller roles"),
    )
    for key, label in labels:
        values = [str(value) for value in rig_editability.get(key, [])]
        if values:
            failures.append("{}: {}".format(label, ", ".join(sorted(values))))
    return failures


def _scene_evidence(
    cmds: Any,
    new_nodes: Any,
    required_controller_roles: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
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
    rig_editability = _rig_editability_evidence(cmds, new_set, required_controller_roles)
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
        "rig_editability": rig_editability,
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
    required_constrained_controller_roles: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    try:
        from maya import cmds

        Store, _, _ = _core_types()
        required_controller_roles = _normalize_required_controller_roles(required_constrained_controller_roles)
        if required_controller_roles and editability_mode != "native":
            return skill_error(
                "Native controllers require native editability mode",
                "required_constrained_controller_roles cannot be verified in usd_proxy mode",
                required_roles=required_controller_roles,
            )
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
        evidence = _scene_evidence(cmds, new_nodes, required_controller_roles)
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
        controller_failures = _required_controller_failures(evidence["rig_editability"])
        if required_controller_roles and controller_failures:
            return skill_error(
                "Maya did not preserve required constrained controllers",
                "The synchronized native rig is missing editable controller or constraint evidence",
                failures=controller_failures,
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
