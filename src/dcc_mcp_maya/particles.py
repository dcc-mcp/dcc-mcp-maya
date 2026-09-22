"""Small, typed boundary around Maya's particle-system commands.

The functions accept a ``maya.cmds``-compatible object so the particle contract
can be unit tested without importing Maya.  Skill entry points remain
responsible for lazy host imports and result-envelope handling.

Covers both families Maya ships:

* **nParticle** (``cmds.nParticle``) — Nucleus-driven particles, the modern
  default for anything that should collide with nCloth / nRigid or be cached.
* **classic particles** (``cmds.particle``) — legacy ``particle`` nodes, still
  what a lot of old rigs and MEL scripts expect.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

NPARTICLE_NODE_TYPE = "nParticle"
PARTICLE_NODE_TYPE = "particle"
EMITTER_NODE_TYPE = "pointEmitter"
INSTANCER_NODE_TYPE = "instancer"

#: ``create_emitter`` emitter types and the ``maya.cmds`` factory for each.
EMITTER_COMMANDS: Dict[str, str] = {
    "omni": "emitter",
    "directional": "emitter",
    "surface": "emitter",
    "curve": "emitter",
    "volume": "emitter",
}

#: ``cmds.emitter -type`` values Maya understands.
EMITTER_TYPES: Tuple[str, ...] = ("omni", "directional", "surface", "curve", "volume")

#: Particle render types for nParticle shapes.
NPARTICLE_RENDER_TYPES: Tuple[str, ...] = (
    "points",
    "multiPoint",
    "numeric",
    "spheres",
    "sprites",
    "streak",
    "blobby",
    "cloud",
    "tube",
)

#: ``cmds.particleInstancer -cycle`` values accepted by Maya.
#: Maya rejects anything else, including ``random``.
CYCLE_MODES: Tuple[str, ...] = ("none", "sequential")


NPARTICLE_ATTRS: Dict[str, str] = {
    "lifespan_mode": "lifespanMode",
    "lifespan": "lifespan",
    "lifespan_random": "lifespanRandom",
    "particle_render_type": "particleRenderType",
    "radius": "radius",
    "radius_scale": "radiusScale",
    "radius_scale_random": "radiusScaleRandom",
    "conserve": "conserve",
    "drag": "drag",
    "damp": "damp",
    "mass": "mass",
    "bounce": "bounce",
    "friction": "friction",
    "collide": "collide",
    "collide_width_scale": "collideWidthScale",
    "self_collide": "selfCollide",
    "self_collide_width_scale": "selfCollideWidthScale",
    "max_trail_size": "maxTrailSize",
    "opacity": "opacity",
    "color_red": "colorRed",
    "color_green": "colorGreen",
    "color_blue": "colorBlue",
    "incandescence_red": "incandescenceRed",
    "incandescence_green": "incandescenceGreen",
    "incandescence_blue": "incandescenceBlue",
    "is_dynamic": "isDynamic",
    "dynamics_weight": "dynamicsWeight",
    "goal_weight": "goalWeight",
    "goal_smoothness": "goalSmoothness",
    "count": "count",
    "inherit_factor": "inheritFactor",
    "max_count": "maxCount",
    "level_of_detail": "levelOfDetail",
    "random_seed": "randomSeed",
}

PARTICLE_ATTRS: Dict[str, str] = {
    "conserve": "conserve",
    "lifespan_mode": "lifespanMode",
    "lifespan": "lifespan",
    "lifespan_random": "lifespanRandom",
    "particle_render_type": "particleRenderType",
    "radius": "radius",
    "inherit_factor": "inheritFactor",
    "is_dynamic": "isDynamic",
    "dynamics_weight": "dynamicsWeight",
    "count": "count",
}

EMITTER_ATTRS: Dict[str, str] = {
    "rate": "rate",
    "scale_rate_by_object_size": "scaleRateByObjectSize",
    "need_parent_uv": "needParentUV",
    "cycle_emission": "cycleEmission",
    "cycle_interval": "cycleInterval",
    "speed": "speed",
    "speed_random": "speedRandom",
    "tangent_speed": "tangentSpeed",
    "normal_speed": "normalSpeed",
    "spread": "spread",
    "random_direction": "randomDirection",
    "direction": "direction",
    "direction_rate": "directionRate",
    "scale_speed_by_size": "scaleSpeedBySize",
    "display_speed": "displaySpeed",
    "use_distance": "useDistance",
    "min_distance": "minDistance",
    "max_distance": "maxDistance",
    "particle_type": "type",
    "emitter_type": "emitterType",
    "inward_speed": "inwardSpeed",
    "around_axis": "aroundAxis",
    "along_axis": "alongAxis",
    "away_from_center": "awayFromCenter",
    "away_from_axis": "awayFromAxis",
    "volume_shape": "volumeShape",
    "volume_offset": "volumeOffset",
    "volume_sweep": "volumeSweep",
    "section_radius": "sectionRadius",
    "die_on_emission_volume_exit": "dieOnEmissionVolumeExit",
    "random_seed": "randomSeed",
}


class ParticleContractError(ValueError):
    """Raised when a requested particle operation is malformed."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def as_str_list(value: Any) -> List[str]:
    """Normalise a scalar / list tool argument into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [str(item) for item in value if str(item).strip()]


def snapshot_nodes(cmds: Any, node_types: Sequence[str]) -> Set[str]:
    """Return the long names of every node of the given types."""
    found: Set[str] = set()
    for node_type in node_types:
        for node in cmds.ls(type=node_type, long=True) or []:
            found.add(str(node))
    return found


def new_nodes(before: Set[str], cmds: Any, node_types: Sequence[str]) -> List[str]:
    """Return nodes of ``node_types`` created since ``before`` was taken."""
    return sorted(snapshot_nodes(cmds, node_types) - before)


def parent_transforms(cmds: Any, nodes: Sequence[str]) -> List[str]:
    """Return the parent transform for each shape node."""
    transforms: List[str] = []
    for node in nodes:
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        if parents:
            transforms.append(str(parents[0]))
    return transforms


def _plug_value(value: Any) -> Any:
    """Coerce a tool value into something ``cmds.setAttr`` accepts."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return value


def set_node_attrs(cmds: Any, node: str, attrs: Mapping[str, Any], attr_map: Mapping[str, str]) -> Dict[str, Any]:
    """Set recognised attributes on ``node`` and return what was applied."""
    applied: Dict[str, Any] = {}
    unknown = [key for key in attrs if key not in attr_map]
    if unknown:
        raise ParticleContractError(
            "Unsupported attribute(s) for {}: {}. Supported: {}".format(
                node,
                ", ".join(sorted(unknown)),
                ", ".join(sorted(attr_map)),
            )
        )
    for key in sorted(attrs):
        raw = attrs[key]
        if raw is None:
            continue
        value = _plug_value(raw)
        if isinstance(value, list):
            if len(value) != 3:
                raise ParticleContractError("{} expects 3 components, got {}".format(key, len(value)))
            cmds.setAttr(
                "{}.{}".format(node, attr_map[key]),
                value[0],
                value[1],
                value[2],
                type="double3",
            )
        else:
            cmds.setAttr("{}.{}".format(node, attr_map[key]), value)
        applied[key] = raw
    return applied


def resolve_shape(cmds: Any, node: str, expected_types: Sequence[str]) -> str:
    """Resolve ``node`` to a shape of one of ``expected_types``."""
    name = str(node or "").strip()
    if not name:
        raise ParticleContractError("node must be a non-empty Maya node name")
    if not cmds.objExists(name):
        raise ParticleContractError("Node does not exist: {}".format(name))
    node_type = str(cmds.nodeType(name))
    if node_type in expected_types:
        return name
    shapes = cmds.listRelatives(name, shapes=True, fullPath=True) or []
    matches = [str(shape) for shape in shapes if str(cmds.nodeType(shape)) in expected_types]
    if matches:
        return matches[0]
    raise ParticleContractError("{} is a {} and has no {} shape".format(name, node_type, " / ".join(expected_types)))


def _first_created(created: Any) -> Optional[str]:
    """Normalise the return value of a Maya create command to a node name."""
    if isinstance(created, (list, tuple)):
        return str(created[0]) if created else None
    if created:
        return str(created)
    return None


# ---------------------------------------------------------------------------
# Particle systems
# ---------------------------------------------------------------------------


def create_particle_system(
    cmds: Any,
    kind: str = "nparticle",
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    properties: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an nParticle or classic particle system."""
    system_kind = str(kind or "nparticle").strip().lower()
    if system_kind not in ("nparticle", "classic"):
        raise ParticleContractError("kind must be 'nparticle' or 'classic'")

    node_type = NPARTICLE_NODE_TYPE if system_kind == "nparticle" else PARTICLE_NODE_TYPE
    factory = cmds.nParticle if system_kind == "nparticle" else cmds.particle

    before = snapshot_nodes(cmds, (node_type,))
    kwargs: Dict[str, Any] = {}
    requested = str(name or "").strip()
    if requested:
        kwargs["name"] = requested
    if position:
        triple = [float(item) for item in position]
        if len(triple) != 3:
            raise ParticleContractError("position expects 3 components, got {}".format(len(triple)))
        kwargs["position"] = triple

    created = factory(**kwargs)
    shapes = new_nodes(before, cmds, (node_type,))
    shape = shapes[0] if shapes else _first_created(created)
    if not shape:
        raise ParticleContractError("Maya did not return a particle shape")

    applied: Dict[str, Any] = {}
    if properties:
        attr_map = NPARTICLE_ATTRS if system_kind == "nparticle" else PARTICLE_ATTRS
        applied = set_node_attrs(cmds, shape, properties, attr_map)

    transforms = parent_transforms(cmds, [shape])
    return {
        "kind": system_kind,
        "shape": shape,
        "transform": transforms[0] if transforms else None,
        "properties": applied,
    }


def set_particle_properties(
    cmds: Any,
    nodes: Sequence[str],
    properties: Mapping[str, Any],
) -> Dict[str, Any]:
    """Edit attributes on nParticle / classic particle shapes."""
    if not properties:
        raise ParticleContractError("properties must contain at least one attribute")
    updated: List[Dict[str, Any]] = []
    for node in as_str_list(nodes):
        name = str(node or "").strip()
        if not cmds.objExists(name):
            raise ParticleContractError("Node does not exist: {}".format(name))
        node_type = str(cmds.nodeType(name))
        if node_type == NPARTICLE_NODE_TYPE:
            applied = set_node_attrs(cmds, name, properties, NPARTICLE_ATTRS)
        else:
            shape = resolve_shape(cmds, name, (NPARTICLE_NODE_TYPE, PARTICLE_NODE_TYPE))
            attr_map = NPARTICLE_ATTRS if str(cmds.nodeType(shape)) == NPARTICLE_NODE_TYPE else PARTICLE_ATTRS
            applied = set_node_attrs(cmds, shape, properties, attr_map)
            name = shape
        updated.append({"particle": name, "properties": applied})
    if not updated:
        raise ParticleContractError("nodes must name at least one particle shape")
    return {"updated": updated, "count": len(updated)}


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------


def create_emitter(
    cmds: Any,
    emitter_type: str = "omni",
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    targets: Optional[Sequence[str]] = None,
    properties: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an emitter and optionally connect it to particle systems."""
    etype = str(emitter_type or "omni").strip().lower()
    if etype not in EMITTER_TYPES:
        raise ParticleContractError("emitter_type must be one of: {}".format(", ".join(EMITTER_TYPES)))

    kwargs: Dict[str, Any] = {"type": etype}
    requested = str(name or "").strip()
    if requested:
        kwargs["name"] = requested
    if position:
        triple = [float(item) for item in position]
        if len(triple) != 3:
            raise ParticleContractError("position expects 3 components, got {}".format(len(triple)))
        kwargs["position"] = triple

    created = cmds.emitter(**kwargs)
    emitter = _first_created(created)
    if not emitter:
        raise ParticleContractError("Maya did not return an emitter node")

    applied: Dict[str, Any] = {}
    if properties:
        applied = set_node_attrs(cmds, emitter, properties, EMITTER_ATTRS)

    connected: List[str] = []
    for target in as_str_list(targets):
        if not cmds.objExists(target):
            raise ParticleContractError("Particle node does not exist: {}".format(target))
        cmds.connectDynamic(target, em=emitter)
        connected.append(target)

    parents = parent_transforms(cmds, [emitter])
    return {
        "emitter": emitter,
        "emitter_type": etype,
        "transform": parents[0] if parents else None,
        "properties": applied,
        "targets": connected,
    }


def set_emitter_properties(
    cmds: Any,
    emitters: Sequence[str],
    properties: Mapping[str, Any],
) -> Dict[str, Any]:
    """Edit attributes on existing emitter nodes."""
    if not properties:
        raise ParticleContractError("properties must contain at least one attribute")
    updated: List[Dict[str, Any]] = []
    for node in as_str_list(emitters):
        name = str(node or "").strip()
        if not cmds.objExists(name):
            raise ParticleContractError("Emitter does not exist: {}".format(name))
        applied = set_node_attrs(cmds, name, properties, EMITTER_ATTRS)
        updated.append({"emitter": name, "properties": applied})
    if not updated:
        raise ParticleContractError("emitters must name at least one emitter node")
    return {"updated": updated, "count": len(updated)}


# ---------------------------------------------------------------------------
# Instancing
# ---------------------------------------------------------------------------


def create_particle_instancer(
    cmds: Any,
    particle: str,
    objects: Sequence[str],
    name: Optional[str] = None,
    cycle: str = "none",
    rotation_units: str = "Degrees",
    level_of_detail: str = "Geometry",
) -> Dict[str, Any]:
    """Instance source geometry onto a particle system."""
    shape = resolve_shape(cmds, particle, (NPARTICLE_NODE_TYPE, PARTICLE_NODE_TYPE))
    sources = as_str_list(objects)
    if not sources:
        raise ParticleContractError("objects must name at least one source object")
    for obj in sources:
        if not cmds.objExists(obj):
            raise ParticleContractError("Source object does not exist: {}".format(obj))

    # Maya's `-cycle` only accepts "none" or "sequential"; anything else is
    # rejected by the command itself, so validate here to fail with a clear message.
    cycle_mode = str(cycle or "none").strip().lower()
    if cycle_mode not in CYCLE_MODES:
        raise ParticleContractError("cycle must be one of: {}".format(", ".join(CYCLE_MODES)))

    kwargs: Dict[str, Any] = {
        "addObject": True,
        "object": sources,
        "cycle": cycle_mode,
        "rotationUnits": str(rotation_units),
        "levelOfDetail": str(level_of_detail),
    }
    requested = str(name or "").strip()
    if requested:
        kwargs["name"] = requested
    created = cmds.particleInstancer(shape, **kwargs)
    instancer = _first_created(created)

    nodes = [str(item) for item in (cmds.ls(type=INSTANCER_NODE_TYPE, long=True) or [])]
    return {
        "instancer": instancer or (nodes[0] if nodes else None),
        "particle": shape,
        "objects": sources,
        "cycle": cycle_mode,
    }


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


PARTICLE_QUERY_TYPES: Tuple[str, ...] = (
    NPARTICLE_NODE_TYPE,
    PARTICLE_NODE_TYPE,
    "pointEmitter",
    "directionEmitter",
    "surfaceEmitter",
    "volumeEmitter",
    "curveEmitter",
    INSTANCER_NODE_TYPE,
)


def list_particles(cmds: Any, include_emitters: bool = True, include_instancers: bool = True) -> Dict[str, Any]:
    """Summarise the particle systems, emitters and instancers in the scene."""
    systems: List[Dict[str, Any]] = []
    for node_type in (NPARTICLE_NODE_TYPE, PARTICLE_NODE_TYPE):
        for node in sorted(snapshot_nodes(cmds, (node_type,))):
            systems.append(_describe_particle(cmds, node, node_type))

    emitters: List[Dict[str, Any]] = []
    if include_emitters:
        for node_type in ("pointEmitter", "directionEmitter", "surfaceEmitter", "volumeEmitter", "curveEmitter"):
            for node in sorted(snapshot_nodes(cmds, (node_type,))):
                emitters.append(_describe_emitter(cmds, node, node_type))

    instancers: List[Dict[str, Any]] = []
    if include_instancers:
        for node in sorted(snapshot_nodes(cmds, (INSTANCER_NODE_TYPE,))):
            instancers.append(_describe_instancer(cmds, node))

    return {
        "particle_systems": systems,
        "emitters": emitters,
        "instancers": instancers,
        "counts": {
            "particle_systems": len(systems),
            "emitters": len(emitters),
            "instancers": len(instancers),
        },
    }


def _safe_get_attr(cmds: Any, plug: str) -> Any:
    """Read an attribute, returning ``None`` when the plug is unavailable."""
    try:
        if cmds.objExists(plug):
            return cmds.getAttr(plug)
    except Exception:  # noqa: BLE001 - introspection must never fail the call
        return None
    return None


def _describe_particle(cmds: Any, node: str, node_type: str) -> Dict[str, Any]:
    """Build a summary record for one particle shape."""
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    record: Dict[str, Any] = {
        "shape": node,
        "node_type": node_type,
        "transform": str(parents[0]) if parents else None,
        "kind": "nparticle" if node_type == NPARTICLE_NODE_TYPE else "classic",
    }
    if node_type == NPARTICLE_NODE_TYPE:
        record["count"] = _safe_get_attr(cmds, "{}.count".format(node))
        record["is_dynamic"] = _safe_get_attr(cmds, "{}.isDynamic".format(node))
    else:
        record["count"] = _safe_get_attr(cmds, "{}.count".format(node))
    emitters = cmds.listConnections(node, type="pointEmitter", source=True, destination=False) or []
    record["emitters"] = [str(item) for item in emitters]
    return record


def _describe_emitter(cmds: Any, node: str, node_type: str) -> Dict[str, Any]:
    """Build a summary record for one emitter."""
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    record: Dict[str, Any] = {
        "emitter": node,
        "node_type": node_type,
        "transform": str(parents[0]) if parents else None,
        "rate": _safe_get_attr(cmds, "{}.rate".format(node)),
    }
    targets = cmds.listConnections(node, type=NPARTICLE_NODE_TYPE, source=False, destination=True) or []
    if not targets:
        targets = cmds.listConnections(node, type=PARTICLE_NODE_TYPE, source=False, destination=True) or []
    record["targets"] = [str(item) for item in targets]
    return record


def _describe_instancer(cmds: Any, node: str) -> Dict[str, Any]:
    """Build a summary record for one particle instancer."""
    record: Dict[str, Any] = {"instancer": node}
    inputs = cmds.listConnections(node, type=NPARTICLE_NODE_TYPE, source=True, destination=False) or []
    if not inputs:
        inputs = cmds.listConnections(node, type=PARTICLE_NODE_TYPE, source=True, destination=False) or []
    record["particles"] = [str(item) for item in inputs]
    return record
