"""Export normalized Maya polygon modeling state."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

SCHEMA_NAME = "dcc-mcp/model-state"
SCHEMA_VERSION = 1
CHECK_NAMES = ("parts", "hierarchy", "materials", "uv_coverage", "non_manifold", "euler")
_MAX_OBJECTS = 128

_HISTORY_ATTRIBUTES = {
    "loft": ("degree", "uniform", "close", "sectionSpans"),
    "revolve": ("segments", "startSweep", "endSweep", "axis"),
    "polyExtrudeFace": ("localTranslateX", "localTranslateY", "localTranslateZ", "thickness", "keepFacesTogether"),
    "polyExtrudeEdge": ("localTranslateX", "localTranslateY", "localTranslateZ", "thickness"),
    "polyBevel": ("offset", "segments", "autoFit", "mergeVertices"),
    "polyBevel2": ("offset", "segments", "autoFit", "mergeVertices"),
    "polyBevel3": ("offset", "segments", "autoFit", "mergeVertices"),
    "polyMirrorFace": ("axis", "axisDirection", "cutMesh", "mergeMode", "mergeThreshold", "axisPos"),
}


def _number(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("value must be finite")
    return result


def _vector(value: Any, length: int = 3) -> List[float]:
    if value is None or isinstance(value, (str, bytes)):
        raise ValueError("vector is unavailable")
    values = list(value)
    if len(values) < length:
        raise ValueError("vector has too few components")
    return [_number(values[index]) for index in range(length)]


def _first(value: Any) -> Optional[str]:
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return str(value) if value else None


def _short_name(value: str) -> str:
    return value.rsplit("|", 1)[-1]


def _query(cmds: Any, function_name: str, *args: Any, **kwargs: Any) -> Tuple[Any, bool]:
    function = getattr(cmds, function_name, None)
    if not callable(function):
        return None, False
    try:
        return function(*args, **kwargs), True
    except Exception:
        return None, False


def _resolve_transform(cmds: Any, object_name: str) -> Optional[str]:
    matches, available = _query(cmds, "ls", object_name, long=True)
    if not available or not isinstance(matches, (list, tuple)) or len(matches) != 1:
        return None
    node = str(matches[0])
    node_type, type_available = _query(cmds, "nodeType", node)
    if type_available and node_type == "mesh":
        parents, parents_available = _query(cmds, "listRelatives", node, parent=True, fullPath=True)
        return _first(parents) if parents_available else None
    return node


def _mesh_shape(cmds: Any, transform: str) -> Optional[str]:
    shapes, available = _query(
        cmds, "listRelatives", transform, shapes=True, noIntermediate=True, type="mesh", fullPath=True
    )
    if not available or not isinstance(shapes, (list, tuple)):
        return None
    return _first(shapes)


def _world_bounds(cmds: Any, transform: str) -> Optional[Dict[str, Any]]:
    values, available = _query(cmds, "exactWorldBoundingBox", transform)
    if not available or not isinstance(values, (list, tuple)) or len(values) < 6:
        return None
    try:
        return {
            "min": [_number(value) for value in values[:3]],
            "max": [_number(value) for value in values[3:6]],
            "space": "world",
        }
    except (TypeError, ValueError):
        return None


def _materials(cmds: Any, shape: str) -> Tuple[List[str], bool]:
    shading_engines, available = _query(cmds, "listConnections", shape + ".instObjGroups", type="shadingEngine")
    if not available:
        return [], False
    if shading_engines is None:
        return [], True
    if not isinstance(shading_engines, (list, tuple)):
        return [], False
    names: List[str] = []
    for shading_engine in shading_engines:
        connections, connected = _query(cmds, "listConnections", str(shading_engine) + ".surfaceShader")
        if not connected:
            return names, False
        for material in connections or []:
            material_name = str(material)
            if material_name and material_name not in names:
                names.append(material_name)
    return names, True


def _non_manifold(cmds: Any, shape: str) -> Tuple[Optional[bool], bool, Optional[str]]:
    findings: List[str] = []
    for flag, label in (("nonManifoldVertices", "vertices"), ("nonManifoldEdges", "edges")):
        result, available = _query(cmds, "polyInfo", shape, **{flag: True})
        if not available:
            return None, False, "polyInfo.{}".format(label)
        if result:
            if isinstance(result, (list, tuple)):
                findings.extend(str(item) for item in result)
            else:
                return None, False, "polyInfo.{}".format(label)
    return bool(findings), True, None


def _history(cmds: Any, transform: str) -> List[Dict[str, Any]]:
    values, available = _query(cmds, "listHistory", transform, pruneDagObjects=True)
    if not available or not isinstance(values, (list, tuple)):
        return []
    evidence: List[Dict[str, Any]] = []
    for node in values:
        node_name = str(node)
        node_type, type_available = _query(cmds, "nodeType", node_name)
        if not type_available:
            continue
        attributes = _HISTORY_ATTRIBUTES.get(str(node_type), ())
        readback: Dict[str, Any] = {}
        for attribute in attributes:
            value, value_available = _query(cmds, "getAttr", "{}.{}".format(node_name, attribute))
            if value_available and not hasattr(value, "_mock_name"):
                if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], (list, tuple)):
                    value = value[0]
                try:
                    readback[attribute] = _number(value) if isinstance(value, (int, float)) else value
                except (TypeError, ValueError):
                    readback[attribute] = value
        evidence.append({"node": node_name, "type": str(node_type), "parameters": readback})
    return evidence


def _transform_state(cmds: Any, transform: str, unavailable: Set[str]) -> Dict[str, Any]:
    state: Dict[str, Any] = {"name": _short_name(transform), "transform": {"object_path": transform}}
    try:
        translation, ok_translation = _query(cmds, "xform", transform, query=True, worldSpace=True, translation=True)
        rotation, ok_rotation = _query(cmds, "xform", transform, query=True, worldSpace=True, rotation=True)
        scale, ok_scale = _query(cmds, "getAttr", transform + ".scale")
        state["transform"]["location"] = _vector(translation)
        state["transform"]["rotation"] = _vector(rotation)
        state["transform"]["scale"] = _vector(
            scale[0] if isinstance(scale, (list, tuple)) and len(scale) == 1 else scale
        )
        state["euler"] = state["transform"]["rotation"]
        if not (ok_translation and ok_rotation and ok_scale):
            raise ValueError("transform query unavailable")
    except (TypeError, ValueError):
        unavailable.add("euler")
    pivots, pivot_available = _query(cmds, "xform", transform, query=True, worldSpace=True, pivots=True)
    if pivot_available:
        try:
            values = _vector(pivots, length=6)
            state["transform"]["rotate_pivot"] = values[:3]
            state["transform"]["scale_pivot"] = values[3:]
        except (TypeError, ValueError):
            pass
    state["native_history"] = _history(cmds, transform)
    return state


def _mesh_state(cmds: Any, transform: str, shape: str, unavailable: Set[str]) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "name": _short_name(transform),
        "uv_sets": 0,
        "material": None,
        "is_non_manifold": False,
        "vertex_count": 0,
    }
    for key, flag in (("vertex_count", "vertex"), ("edge_count", "edge"), ("face_count", "face")):
        value, available = _query(cmds, "polyEvaluate", shape, **{flag: True})
        if available:
            try:
                state[key] = int(value)
            except (TypeError, ValueError):
                unavailable.add("parts")
        else:
            unavailable.add("parts")

    uv_sets, uv_available = _query(cmds, "polyUVSet", shape, query=True, allUVSets=True)
    if uv_available and isinstance(uv_sets, (list, tuple)):
        state["uv_sets"] = len(uv_sets)
        uv_counts: Dict[str, int] = {}
        for uv_set in uv_sets:
            count, count_available = _query(cmds, "polyEvaluate", shape, uvcoord=True, uvSetName=str(uv_set))
            if not count_available:
                unavailable.add("uv_coverage")
                continue
            try:
                uv_counts[str(uv_set)] = int(count)
            except (TypeError, ValueError):
                unavailable.add("uv_coverage")
        state["uv_counts"] = uv_counts
        state["uv_count"] = sum(uv_counts.values())
    else:
        unavailable.add("uv_coverage")

    materials, materials_available = _materials(cmds, shape)
    if materials_available:
        state["material"] = materials[0] if materials else None
        if len(materials) > 1:
            state["materials"] = materials
    else:
        unavailable.add("materials")

    manifold, manifold_available, manifold_source = _non_manifold(cmds, shape)
    if manifold_available:
        state["is_non_manifold"] = bool(manifold)
    else:
        unavailable.add("non_manifold")
        state["non_manifold_readback"] = {"available": False, "source": manifold_source}

    bounds = _world_bounds(cmds, transform)
    if bounds is not None:
        state["bounds"] = bounds
    return state


def _resolve_targets(cmds: Any, object_names: Optional[List[str]], max_objects: int) -> Tuple[List[str], List[str]]:
    if object_names:
        if len(object_names) > _MAX_OBJECTS:
            return [], ["object_names exceeds {} objects".format(_MAX_OBJECTS)]
        transforms: List[str] = []
        missing: List[str] = []
        for object_name in object_names:
            transform = _resolve_transform(cmds, object_name)
            if transform is None:
                missing.append(object_name)
            elif transform not in transforms:
                transforms.append(transform)
        return transforms, missing
    meshes, available = _query(cmds, "ls", type="mesh", long=True)
    if not available or not isinstance(meshes, (list, tuple)):
        return [], ["Maya mesh inventory unavailable"]
    transforms = []
    for shape in meshes:
        parent, parent_available = _query(cmds, "listRelatives", shape, parent=True, fullPath=True)
        transform = _first(parent) if parent_available else None
        if transform and transform not in transforms:
            transforms.append(transform)
    return transforms[:max_objects], []


def _build_state(cmds: Any, transforms: Iterable[str]) -> Dict[str, Any]:
    unavailable: Set[str] = set()
    parts: List[str] = []
    hierarchy: List[str] = []
    meshes: List[Dict[str, Any]] = []
    objects: List[Dict[str, Any]] = []
    for transform in transforms:
        parts.append(_short_name(transform))
        hierarchy.append(transform)
        object_state = _transform_state(cmds, transform, unavailable)
        objects.append(object_state)
        shape = _mesh_shape(cmds, transform)
        if shape is not None:
            meshes.append(_mesh_state(cmds, transform, shape, unavailable))
        else:
            unavailable.add("parts")
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "partial": bool(unavailable),
        "unavailable": sorted(unavailable),
        "parts": parts,
        "hierarchy": hierarchy,
        "meshes": meshes,
        "objects": objects,
    }


def export_model_state(object_names: Optional[List[str]] = None, max_objects: int = 64) -> dict:
    """Export bounded, JSON-safe Maya modeling state."""
    if isinstance(max_objects, bool) or not isinstance(max_objects, int) or not 1 <= max_objects <= _MAX_OBJECTS:
        return skill_error("Invalid max_objects", "max_objects must be an integer from 1 to 128")
    if object_names is not None and (
        not isinstance(object_names, list)
        or not object_names
        or any(not isinstance(name, str) or not name for name in object_names)
    ):
        return skill_error("Invalid object_names", "object_names must be a non-empty list of names")
    try:
        import maya.cmds as cmds

        transforms, issues = _resolve_targets(cmds, object_names, max_objects)
        if issues:
            return skill_error("Could not resolve modeling scope", "Maya modeling scope is incomplete", issues=issues)
        state = _build_state(cmds, transforms)
        return skill_success(
            "Maya modeling state exported",
            state=state,
            object_count=len(state["objects"]),
            mesh_count=len(state["meshes"]),
            partial=state["partial"],
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to export Maya modeling state")


@skill_entry
def main(**kwargs) -> dict:
    return export_model_state(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
