"""Small, typed boundary around Maya's Nucleus dynamics commands.

The functions in this module accept a ``maya.cmds``-compatible object so the
Nucleus contract can be unit tested without importing Maya.  Skill entry points
remain responsible for lazy host imports and result-envelope handling.

Coverage (batch 1 of the native-capability expansion):

* nCloth — ``nClothCreate`` + per-shape property edits.
* nRigid — passive collision objects.
* nConstraint — the Nucleus constraint family.
* nucleus — the solver node and its global settings.
* dynamic fields — the full ``air`` … ``volumeAxis`` create surface plus
  property edits, built on top of the classic :mod:`gravity` helpers that the
  ``maya-dynamics`` skill already shipped.
* nCache — ``cacheFile`` based write / attach / delete.
"""

from __future__ import annotations

# Import built-in modules
import glob
import os
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

NCLOTH_NODE_TYPE = "nCloth"
NRIGID_NODE_TYPE = "nRigid"
NUCLEUS_NODE_TYPE = "nucleus"

#: Nucleus constraint types accepted by ``cmds.nConstraint``.
NCONSTRAINT_TYPES: Tuple[str, ...] = (
    "transform",
    "componentToComponent",
    "pointToPoint",
    "weld",
    "slideOnSurface",
    "forceField",
    "attractToMatchingMesh",
    "tearableSurface",
    "disableCollision",
    "excludeCollisionPairs",
)

#: Classic rigid-body constraint types accepted by ``cmds.rigidConstraint``.
RIGID_CONSTRAINT_TYPES: Tuple[str, ...] = ("nail", "pin", "hinge", "spring", "barrier")

#: ``create_dynamic_field`` field type -> ``maya.cmds`` factory name.
FIELD_COMMANDS: Dict[str, str] = {
    "air": "air",
    "drag": "drag",
    "gravity": "gravity",
    "newton": "newton",
    "radial": "radial",
    "turbulence": "turbulence",
    "uniform": "uniform",
    "vortex": "vortex",
    "volume_axis": "volumeAxis",
}

#: Maya node type that ``cmds.cacheFile`` creates to own an nCache.
CACHE_NODE_TYPE = "cacheFile"

#: Cache file formats accepted by ``cmds.cacheFile``.
CACHE_FORMATS: Tuple[str, ...] = ("OneFile", "OneFilePerFrame")
CACHE_DATA_FORMATS: Tuple[str, ...] = ("mcc", "mcx")

# -- Attribute maps ---------------------------------------------------------
#
# Keys are the snake_case names the MCP tools expose; values are the Maya
# attribute names on the corresponding node.  Keeping the mapping explicit means
# an agent can never smuggle an arbitrary plug name through the typed tool.

NCLOTH_ATTRS: Dict[str, str] = {
    "thickness": "thickness",
    "bounce": "bounce",
    "friction": "friction",
    "damp": "damp",
    "mass": "mass",
    "lift": "lift",
    "drag": "drag",
    "tangential_drag": "tangentialDrag",
    "stretch_resistance": "stretchResistance",
    "compression_resistance": "compressionResistance",
    "bend_resistance": "bendResistance",
    "shear_resistance": "shearResistance",
    "stretch_damp": "stretchDamp",
    "bend_angle_dropoff": "bendAngleDropoff",
    "bend_angle_scale": "bendAngleScale",
    "self_collide": "selfCollide",
    "self_collision_width_scale": "selfCollisionWidthScale",
    "self_collision_softness": "selfCollisionSoftness",
    "push_out": "pushOut",
    "push_out_radius": "pushOutRadius",
    "input_mesh_attract": "inputMeshAttract",
    "rest_iterations": "restIterations",
    "collision_layer": "collisionLayer",
    "wrinkling": "wrinkling",
    "shear_angle_dropoff": "shearAngleDropoff",
    "stretch_angle_scale": "stretchAngleScale",
}

NUCLEUS_ATTRS: Dict[str, str] = {
    "gravity": "gravity",
    "gravity_direction": "gravityDirection",
    "wind_speed": "windSpeed",
    "wind_direction": "windDirection",
    "wind_noise": "windNoise",
    "air_density": "airDensity",
    "substeps": "substeps",
    "max_collision_iterations": "maxCollisionIterations",
    "collision_tolerance": "collisionTolerance",
    "space_scale": "spaceScale",
    "time_scale": "timeScale",
    "start_frame": "startFrame",
    "solver_method": "solverMethod",
    "use_plane": "usePlane",
    "plane_wireframe": "planeWireframe",
}

#: Setting -> Maya node attribute, used by ``set_field_properties`` (setAttr).
#: These are the names the field NODES expose, which differ from the create
#: flags in :data:`FIELD_CREATE_FLAGS` - notably ``applyPerVertex`` here vs
#: ``perVertex`` there, and ``sectionRadius`` here vs ``torusSectionRadius``
#: there. Both were verified against a live Maya 2020-2026 scene.
FIELD_ATTRS: Dict[str, str] = {
    "magnitude": "magnitude",
    "attenuation": "attenuation",
    "max_distance": "maxDistance",
    "apply_per_vertex": "applyPerVertex",
    "frequency": "frequency",
    "phase": "phase",
    "speed": "speed",
    "use_direction": "useDirection",
    "along_axis": "alongAxis",
    "around_axis": "aroundAxis",
    "away_from_center": "awayFromCenter",
    "away_from_axis": "awayFromAxis",
    "directional_speed": "directionalSpeed",
    "turbulence": "turbulence",
    "turbulence_speed": "turbulenceSpeed",
    "turbulence_frequency": "turbulenceFrequency",
    "detail_turbulence": "detailTurbulence",
    "section_radius": "sectionRadius",
    "trap_inside": "trapInside",
    "volume_shape": "volumeShape",
    "invert_attenuation": "invertAttenuation",
    "direction": "direction",
}

#: Create-flag name for each setting, i.e. what ``cmds.<field>(**flags)``
#: accepts.  This is NOT the same vocabulary as :data:`FIELD_ATTRS`: Maya's
#: field *commands* and the nodes they create disagree on several names, and
#: the commands reject what the nodes expose.  Verified against
#: ``cmds.help("<field>")`` on Maya 2020-2026 (identical tables):
#:
#: * ``apply_per_vertex`` is created with ``-perVertex``; the node attribute is
#:   ``applyPerVertex``.  Passing ``applyPerVertex`` to the command raises
#:   ``TypeError: invalid flag 'applyPerVertex'``.
#: * ``vortex`` creates its axis with ``axisX/axisY/axisZ``; it has no
#:   ``directionX/Y/Z`` flag at all.
#: * ``volumeAxis`` creates the section radius with ``torusSectionRadius``
#:   while the node exposes ``sectionRadius``.
#:
#: Settings absent from this map (``directional_strength``, ``trap_inside``,
#: ``turbulence_frequency``) are node attributes only: no field command
#: accepts them, so they are edited with ``set_field_properties`` instead.
FIELD_CREATE_FLAGS: Dict[str, str] = {
    "magnitude": "magnitude",
    "attenuation": "attenuation",
    "max_distance": "maxDistance",
    "apply_per_vertex": "perVertex",
    "speed": "speed",
    "use_direction": "useDirection",
    "frequency": "frequency",
    "phase": "phase",
    "along_axis": "alongAxis",
    "around_axis": "aroundAxis",
    "away_from_center": "awayFromCenter",
    "away_from_axis": "awayFromAxis",
    "directional_speed": "directionalSpeed",
    "turbulence": "turbulence",
    "turbulence_speed": "turbulenceSpeed",
    "detail_turbulence": "detailTurbulence",
    "section_radius": "torusSectionRadius",
    "volume_shape": "volumeShape",
    "invert_attenuation": "invertAttenuation",
}

#: The three create flags ``direction`` expands into.  ``vortex`` is the one
#: field command that names them differently.
DEFAULT_DIRECTION_FLAGS: Tuple[str, str, str] = ("directionX", "directionY", "directionZ")
FIELD_DIRECTION_FLAGS: Dict[str, Tuple[str, str, str]] = {
    "vortex": ("axisX", "axisY", "axisZ"),
}

#: Per-field-type allowlist of the create flags that actually apply.  Keeping
#: this explicit stops agents from passing e.g. ``frequency`` to ``gravity``,
#: which Maya silently ignores and then reports success for.
#:
#: Every entry must name a key of :data:`FIELD_CREATE_FLAGS` (or
#: ``direction``); ``tests/test_maya_nucleus.py::test_field_flag_whitelist``
#: asserts that, and ``test_field_create_flags_exist_in_maya`` re-checks the
#: whole table against ``cmds.help()`` when a real Maya is available.
FIELD_SUPPORTED_FLAGS: Dict[str, Tuple[str, ...]] = {
    "air": ("magnitude", "attenuation", "max_distance", "apply_per_vertex", "speed", "direction"),
    "drag": (
        "magnitude",
        "attenuation",
        "max_distance",
        "apply_per_vertex",
        "direction",
        "use_direction",
    ),
    "gravity": ("magnitude", "attenuation", "max_distance", "apply_per_vertex", "direction"),
    "newton": ("magnitude", "attenuation", "max_distance", "apply_per_vertex"),
    "radial": ("magnitude", "attenuation", "max_distance", "apply_per_vertex"),
    "turbulence": (
        "magnitude",
        "attenuation",
        "max_distance",
        "apply_per_vertex",
        "frequency",
        "phase",
    ),
    "uniform": ("magnitude", "attenuation", "max_distance", "apply_per_vertex", "direction"),
    "vortex": ("magnitude", "attenuation", "max_distance", "apply_per_vertex", "direction"),
    "volume_axis": (
        "magnitude",
        "attenuation",
        "max_distance",
        "apply_per_vertex",
        "direction",
        "along_axis",
        "around_axis",
        "away_from_center",
        "away_from_axis",
        "directional_speed",
        "turbulence",
        "turbulence_speed",
        "turbulence_frequency",
        "detail_turbulence",
        "section_radius",
        "trap_inside",
        "volume_shape",
        "invert_attenuation",
    ),
}

#: Setting -> Maya node attribute, for settings that a field command cannot
#: accept at create time.  ``create_field`` applies these after the node
#: exists so an agent gets the same knobs whether it creates or edits.
FIELD_POST_CREATE_ATTRS: Dict[str, str] = {
    "turbulence_frequency": "turbulenceFrequency",
    "trap_inside": "trapInside",
}

#: Post-create settings whose node attribute is a ``double3``. A scalar reaches
#: ``setAttr`` as one component and Maya then fails with an opaque "error
#: reading data element number 2", so reject it with a usable message.
FIELD_COMPOUND_POST_CREATE: Tuple[str, ...] = ("turbulence_frequency",)

#: Settings that used to be accepted but are neither a create flag nor a node
#: attribute in any Maya build we could check.  They stay recognised so an
#: agent gets an explanation instead of a bare "unsupported key" error.
FIELD_RETIRED_SETTINGS: Dict[str, str] = {
    "directional_strength": "no Maya field command or field node exposes 'directionalStrength'; use "
    "directional_speed for the along-axis push",
}

#: Cache geometry targets accepted by ``cmds.cacheFile -points``.  Restricting
#: to Nucleus / deformable output shapes keeps the tool from silently writing a
#: cache for a transform that has no cachable output geometry.
CACHEABLE_NODE_TYPES: Tuple[str, ...] = ("nCloth", "mesh", "nurbsSurface", "nurbsCurve")


class NucleusContractError(ValueError):
    """Raised when a requested Nucleus operation is malformed."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def as_str_list(value: Any) -> List[str]:
    """Normalise a scalar / list tool argument into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [str(item) for item in value if str(item).strip()]


def validate_targets(cmds: Any, objects: Sequence[str]) -> List[str]:
    """Validate that every requested node exists; return the cleaned list."""
    targets = as_str_list(objects)
    if not targets:
        raise NucleusContractError("objects must name at least one Maya node")
    missing = [name for name in targets if not cmds.objExists(name)]
    if missing:
        raise NucleusContractError("Nodes do not exist: {}".format(", ".join(missing)))
    return targets


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


def select_nodes(cmds: Any, targets: Sequence[str]) -> None:
    """Replace the Maya selection with ``targets``."""
    cmds.select(list(targets), replace=True)


def parent_transforms(cmds: Any, nodes: Sequence[str]) -> List[str]:
    """Return the parent transform for each shape node (empty when none)."""
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
    if isinstance(value, (int, float)):
        return value
    return value


def set_node_attrs(cmds: Any, node: str, attrs: Mapping[str, Any], attr_map: Mapping[str, str]) -> Dict[str, Any]:
    """Set the recognised attributes on ``node`` and return what was applied.

    Unknown keys raise :class:`NucleusContractError` with the supported key list
    so an agent immediately sees the typo instead of getting a silent no-op.
    """
    applied: Dict[str, Any] = {}
    unknown = [key for key in attrs if key not in attr_map]
    if unknown:
        raise NucleusContractError(
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
        attr_name = attr_map[key]
        value = _plug_value(raw)
        if isinstance(value, list):
            if len(value) != 3:
                raise NucleusContractError("{} expects 3 components, got {}".format(key, len(value)))
            cmds.setAttr(
                "{}.{}".format(node, attr_name),
                value[0],
                value[1],
                value[2],
                type="double3",
            )
        else:
            cmds.setAttr("{}.{}".format(node, attr_name), value)
        applied[key] = raw
    return applied


def resolve_shape(cmds: Any, node: str, expected_types: Sequence[str]) -> str:
    """Resolve ``node`` to a shape of one of ``expected_types``."""
    name = str(node or "").strip()
    if not name:
        raise NucleusContractError("node must be a non-empty Maya node name")
    if not cmds.objExists(name):
        raise NucleusContractError("Node does not exist: {}".format(name))
    node_type = str(cmds.nodeType(name))
    if node_type in expected_types:
        return name
    shapes = cmds.listRelatives(name, shapes=True, fullPath=True) or []
    matches = [str(shape) for shape in shapes if str(cmds.nodeType(shape)) in expected_types]
    if matches:
        return matches[0]
    raise NucleusContractError("{} is a {} and has no {} shape".format(name, node_type, " / ".join(expected_types)))


# ---------------------------------------------------------------------------
# nCloth / nRigid / nConstraint / nucleus
# ---------------------------------------------------------------------------


def create_ncloth(
    cmds: Any,
    objects: Sequence[str],
    name: Optional[str] = None,
    local_space_output: bool = False,
    properties: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create one nCloth node per target mesh and return their identities."""
    targets = validate_targets(cmds, objects)
    before_cloth = snapshot_nodes(cmds, (NCLOTH_NODE_TYPE,))
    before_solver = snapshot_nodes(cmds, (NUCLEUS_NODE_TYPE,))

    results: List[Dict[str, Any]] = []
    for index, target in enumerate(targets):
        kwargs: Dict[str, Any] = {}
        requested = str(name or "").strip()
        if requested:
            kwargs["name"] = requested if len(targets) == 1 else "{}_{:02d}".format(requested, index + 1)
        if local_space_output:
            kwargs["localSpaceOutput"] = True
        select_nodes(cmds, [target])
        cmds.nClothCreate(**kwargs)

    created_cloth = new_nodes(before_cloth, cmds, (NCLOTH_NODE_TYPE,))
    created_solvers = new_nodes(before_solver, cmds, (NUCLEUS_NODE_TYPE,))
    solver = created_solvers[0] if created_solvers else first_nucleus(cmds)

    for index, cloth in enumerate(created_cloth):
        target = targets[index] if index < len(targets) else None
        applied: Dict[str, Any] = {}
        if properties:
            applied = set_node_attrs(cmds, cloth, properties, NCLOTH_ATTRS)
        results.append(
            {
                "ncloth": cloth,
                "object": target,
                "nucleus": solver,
                "properties": applied,
            }
        )
    return {
        "ncloth_nodes": created_cloth,
        "nucleus": solver,
        "created": results,
        "local_space_output": bool(local_space_output),
    }


def first_nucleus(cmds: Any) -> Optional[str]:
    """Return the first nucleus solver in the scene, if any."""
    nodes = sorted(snapshot_nodes(cmds, (NUCLEUS_NODE_TYPE,)))
    return nodes[0] if nodes else None


def set_cloth_properties(
    cmds: Any,
    nodes: Sequence[str],
    properties: Mapping[str, Any],
) -> Dict[str, Any]:
    """Edit Nucleus cloth attributes on one or more nCloth / nRigid nodes."""
    if not properties:
        raise NucleusContractError("properties must contain at least one attribute")
    updated = []
    for node in as_str_list(nodes):
        shape = resolve_shape(cmds, node, (NCLOTH_NODE_TYPE, NRIGID_NODE_TYPE))
        applied = set_node_attrs(cmds, shape, properties, NCLOTH_ATTRS)
        updated.append({"node": shape, "properties": applied})
    if not updated:
        raise NucleusContractError("nodes must name at least one nCloth or nRigid node")
    return {"updated": updated, "count": len(updated)}


def create_nrigid(
    cmds: Any,
    objects: Sequence[str],
    name: Optional[str] = None,
    properties: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Turn meshes into passive Nucleus collision objects (``nRigid``)."""
    targets = validate_targets(cmds, objects)
    before = snapshot_nodes(cmds, (NRIGID_NODE_TYPE,))

    results: List[Dict[str, Any]] = []
    for index, target in enumerate(targets):
        kwargs: Dict[str, Any] = {}
        requested = str(name or "").strip()
        if requested:
            kwargs["name"] = requested if len(targets) == 1 else "{}_{:02d}".format(requested, index + 1)
        cmds.nRigid(target, **kwargs)

    created = new_nodes(before, cmds, (NRIGID_NODE_TYPE,))
    for index, rigid in enumerate(created):
        applied: Dict[str, Any] = {}
        if properties:
            applied = set_node_attrs(cmds, rigid, properties, NCLOTH_ATTRS)
        results.append(
            {
                "nrigid": rigid,
                "object": targets[index] if index < len(targets) else None,
                "properties": applied,
            }
        )
    return {"nrigid_nodes": created, "created": results}


def create_nconstraint(
    cmds: Any,
    objects: Sequence[str],
    constraint_type: str = "transform",
    name: Optional[str] = None,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a Nucleus constraint between ``target`` (leader) and ``objects``.

    ``target`` is the driver / passive mesh; ``objects`` are the driven nodes.
    Both default to the current selection when omitted.
    """
    ctype = str(constraint_type or "transform").strip()
    if ctype not in NCONSTRAINT_TYPES:
        raise NucleusContractError("constraint_type must be one of: {}".format(", ".join(NCONSTRAINT_TYPES)))

    driven = as_str_list(objects)
    driver = str(target or "").strip()
    if not driven:
        selection = [str(item) for item in (cmds.ls(selection=True, long=True) or [])]
        if not selection:
            raise NucleusContractError("objects (or a selection) is required for a Nucleus constraint")
        driven = selection
    for node in driven:
        if not cmds.objExists(node):
            raise NucleusContractError("Node does not exist: {}".format(node))
    if driver and not cmds.objExists(driver):
        raise NucleusContractError("Target node does not exist: {}".format(driver))

    kwargs: Dict[str, Any] = {"type": ctype}
    requested = str(name or "").strip()
    if requested:
        kwargs["name"] = requested
    cmds.nConstraint(*(driven + ([driver] if driver else [])), **kwargs)
    return {
        "constraint_type": ctype,
        "objects": driven,
        "target": driver or None,
        "name": requested or None,
    }


def create_nucleus_solver(
    cmds: Any,
    name: Optional[str] = None,
    properties: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standalone Nucleus solver node and optionally configure it."""
    kwargs: Dict[str, Any] = {}
    requested = str(name or "").strip()
    if requested:
        kwargs["name"] = requested
    solver = str(cmds.nucleus(**kwargs))
    applied: Dict[str, Any] = {}
    if properties:
        applied = set_node_attrs(cmds, solver, properties, NUCLEUS_ATTRS)
    return {"nucleus": solver, "properties": applied}


def set_nucleus_properties(
    cmds: Any,
    solver: Optional[str] = None,
    properties: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Edit global Nucleus solver settings."""
    if not properties:
        raise NucleusContractError("properties must contain at least one attribute")
    name = str(solver or "").strip()
    if not name:
        detected = first_nucleus(cmds)
        if not detected:
            raise NucleusContractError("No nucleus solver in the scene; pass solver or create one first")
        name = detected
    if not cmds.objExists(name):
        raise NucleusContractError("Nucleus solver does not exist: {}".format(name))
    applied = set_node_attrs(cmds, name, properties, NUCLEUS_ATTRS)
    return {"nucleus": name, "properties": applied}


# ---------------------------------------------------------------------------
# Dynamic fields
# ---------------------------------------------------------------------------


def _field_create_kwargs(
    field_type: str,
    settings: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split tool settings into ``cmds`` create flags and post-create attrs.

    Returns ``(create_kwargs, post_create_attrs)``.  The split matters because
    Maya's field *commands* and the field *nodes* they create use different
    flag vocabularies - see :data:`FIELD_CREATE_FLAGS`.  Passing a node
    attribute name to a create command raises ``TypeError`` at runtime, which
    no fake-``cmds`` unit test can catch; the whitelist plus the meta-test in
    ``tests/test_maya_nucleus.py`` is what keeps the two in step.
    """
    # Retired settings are checked first: they are absent from the whitelist,
    # so the generic message below would otherwise fire and bury the guidance.
    retired = sorted(key for key in settings if key in FIELD_RETIRED_SETTINGS)
    if retired:
        key = retired[0]
        raise NucleusContractError("{}: {}".format(key, FIELD_RETIRED_SETTINGS[key]))

    supported = FIELD_SUPPORTED_FLAGS.get(field_type, ())
    unsupported = [key for key in settings if key not in supported]
    if unsupported:
        raise NucleusContractError(
            "{} field does not support: {}. Supported: {}".format(
                field_type,
                ", ".join(sorted(unsupported)),
                ", ".join(sorted(supported)) or "(none)",
            )
        )

    direction_flags = FIELD_DIRECTION_FLAGS.get(field_type, DEFAULT_DIRECTION_FLAGS)
    create_kwargs: Dict[str, Any] = {}
    post_create: Dict[str, Any] = {}
    for key in sorted(settings):
        value = settings[key]
        if value is None:
            continue
        if key in FIELD_RETIRED_SETTINGS:
            raise NucleusContractError("{}: {}".format(key, FIELD_RETIRED_SETTINGS[key]))
        if key == "direction":
            direction = [float(item) for item in value]
            if len(direction) != 3:
                raise NucleusContractError("direction expects 3 components, got {}".format(len(direction)))
            for flag_name, component in zip(direction_flags, direction):
                create_kwargs[flag_name] = component
            continue
        if key in FIELD_POST_CREATE_ATTRS:
            value = _plug_value(value)
            if key in FIELD_COMPOUND_POST_CREATE and not isinstance(value, list):
                raise NucleusContractError("{} expects a 3-element [x, y, z] list, got a single value".format(key))
            post_create[FIELD_POST_CREATE_ATTRS[key]] = value
            continue
        create_kwargs[FIELD_CREATE_FLAGS[key]] = _plug_value(value)
    return create_kwargs, post_create


def create_field(
    cmds: Any,
    field_type: str,
    name: Optional[str] = None,
    position: Optional[Sequence[float]] = None,
    targets: Optional[Sequence[str]] = None,
    connect: bool = True,
    **settings: Any,
) -> Dict[str, Any]:
    """Create any Maya dynamic field and optionally connect it to targets."""
    ftype = str(field_type or "").strip().lower()
    if ftype not in FIELD_COMMANDS:
        raise NucleusContractError("field_type must be one of: {}".format(", ".join(sorted(FIELD_COMMANDS))))
    factory_name = FIELD_COMMANDS[ftype]
    factory = getattr(cmds, factory_name, None)
    if factory is None:
        raise NucleusContractError("maya.cmds.{} is not available in this Maya build".format(factory_name))

    kwargs, post_create_attrs = _field_create_kwargs(ftype, settings)
    requested = str(name or "").strip()
    if requested:
        kwargs["name"] = requested
    created = factory(**kwargs)
    names: List[str] = []
    if isinstance(created, (list, tuple)):
        names = [str(item) for item in created]
    elif created:
        names = [str(created)]

    field_node = next(
        (item for item in names if str(cmds.nodeType(item)).endswith("Field")),
        names[0] if names else None,
    )

    applied_attrs: Dict[str, Any] = {}
    if field_node and post_create_attrs:
        # Reuse the edit path so compound plugs (``turbulenceFrequency`` is a
        # double3, not a scalar) are set with the right ``type`` argument.
        inverse = {attr: key for key, attr in FIELD_POST_CREATE_ATTRS.items()}
        applied_attrs = set_node_attrs(
            cmds,
            field_node,
            {inverse[attr]: value for attr, value in post_create_attrs.items()},
            FIELD_POST_CREATE_ATTRS,
        )

    if position:
        triple = [float(item) for item in position]
        if len(triple) != 3:
            raise NucleusContractError("position expects 3 components, got {}".format(len(triple)))
        if field_node:
            parents = cmds.listRelatives(field_node, parent=True, fullPath=True) or []
            anchor = str(parents[0]) if parents else field_node
            cmds.setAttr("{}.translate".format(anchor), triple[0], triple[1], triple[2], type="double3")

    connected: List[str] = []
    if field_node and connect and as_str_list(targets):
        connected = connect_field(cmds, as_str_list(targets), field_node)

    return {
        "field": field_node,
        "field_type": ftype,
        "created": names,
        "targets": connected,
        "settings": dict(settings),
        "post_create_attrs": applied_attrs,
    }


def connect_field(
    cmds: Any,
    targets: Sequence[str],
    field: str,
    disconnect: bool = False,
) -> List[str]:
    """Connect (or disconnect) an existing field from dynamic objects."""
    nodes = validate_targets(cmds, targets)
    cmds.connectDynamic(nodes, fields=field, delete=bool(disconnect))
    return nodes


def set_field_properties(
    cmds: Any,
    fields: Sequence[str],
    properties: Mapping[str, Any],
) -> Dict[str, Any]:
    """Edit attributes on existing dynamic field nodes."""
    if not properties:
        raise NucleusContractError("properties must contain at least one attribute")
    updated = []
    for node in as_str_list(fields):
        name = str(node or "").strip()
        if not cmds.objExists(name):
            raise NucleusContractError("Field node does not exist: {}".format(name))
        applied = set_node_attrs(cmds, name, properties, FIELD_ATTRS)
        updated.append({"field": name, "properties": applied})
    if not updated:
        raise NucleusContractError("fields must name at least one dynamic field node")
    return {"updated": updated, "count": len(updated)}


def create_rigid_constraint(
    cmds: Any,
    objects: Sequence[str],
    constraint_type: str = "nail",
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a classic rigid-body constraint (nail / pin / hinge / spring / barrier)."""
    ctype = str(constraint_type or "nail").strip().lower()
    if ctype not in RIGID_CONSTRAINT_TYPES:
        raise NucleusContractError("constraint_type must be one of: {}".format(", ".join(RIGID_CONSTRAINT_TYPES)))
    targets = validate_targets(cmds, objects)
    kwargs: Dict[str, Any] = {"type": ctype}
    requested = str(name or "").strip()
    if requested:
        kwargs["name"] = requested
    created = cmds.rigidConstraint(*targets, **kwargs)
    names: List[str] = []
    if isinstance(created, (list, tuple)):
        names = [str(item) for item in created]
    elif created:
        names = [str(created)]
    return {
        "constraint": names[0] if names else None,
        "constraint_type": ctype,
        "objects": targets,
        "created": names,
    }


# ---------------------------------------------------------------------------
# nCache
# ---------------------------------------------------------------------------


def write_cache(
    cmds: Any,
    nodes: Sequence[str],
    directory: str,
    file_name: Optional[str] = None,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    cache_format: str = "OneFile",
    data_format: str = "mcc",
    world_space: bool = False,
    on_cancelled: Any = None,
) -> Dict[str, Any]:
    """Write one geometry cache per node using ``cmds.cacheFile``."""
    targets = validate_targets(cmds, nodes)
    cache_dir = str(directory or "").strip()
    if not cache_dir:
        raise NucleusContractError("directory is required to write an nCache")
    if cache_format not in CACHE_FORMATS:
        raise NucleusContractError("cache_format must be one of: {}".format(", ".join(CACHE_FORMATS)))
    if data_format not in CACHE_DATA_FORMATS:
        raise NucleusContractError("data_format must be one of: {}".format(", ".join(CACHE_DATA_FORMATS)))

    frame_range = resolve_frame_range(cmds, start_frame, end_frame)

    written: List[Dict[str, Any]] = []
    for index, target in enumerate(targets):
        if on_cancelled is not None:
            on_cancelled()
        shape = resolve_shape(cmds, target, CACHEABLE_NODE_TYPES)
        base = str(file_name or "").strip() or shape.rsplit("|", 1)[-1].rsplit(":", 1)[-1]
        name = base if len(targets) == 1 else "{}_{:02d}".format(base, index + 1)
        kwargs: Dict[str, Any] = {
            "fileName": name,
            "directory": cache_dir,
            "format": cache_format,
            # Maya's flag is -cacheFormat; there is no -dataFormat.
            "cacheFormat": data_format,
            "startTime": frame_range[0],
            "endTime": frame_range[1],
            "points": shape,
            "worldSpace": bool(world_space),
            # Without -createCacheNode Maya writes the cache files but returns a
            # bare file name and never drives the output geometry back.
            "createCacheNode": True,
        }
        created = cmds.cacheFile(**kwargs)
        names: List[str] = []
        if isinstance(created, (list, tuple)):
            names = [str(item) for item in created]
        elif created:
            names = [str(created)]
        cache_node = names[0] if names else None
        if cache_node is None:
            cache_node = _find_cache_node(cmds, shape, name)
        written.append(
            {
                "cache_node": cache_node,
                "node": shape,
                "file_name": name,
                "directory": cache_dir,
                "frame_range": list(frame_range),
            }
        )
    return {"caches": written, "count": len(written), "frame_range": list(frame_range)}


def _find_cache_node(cmds: Any, shape: str, file_name: str, *, strict: bool = False) -> Optional[str]:
    """Best-effort lookup of the cacheFile node attached to ``shape``.

    With ``strict=True`` a miss raises :class:`NucleusContractError` naming the
    reason (ambiguous cacheName vs. no cache at all) instead of returning
    ``None``.  Deletion needs that distinction: ``None`` used to surface as
    "No cacheFile nodes found; pass cache_nodes or scene_nodes", which tells an
    agent to repeat the call it just made even though caches do exist.
    """
    history = cmds.listHistory(shape) or []
    for node in history:
        try:
            if str(cmds.nodeType(node)) == CACHE_NODE_TYPE:
                return str(node)
        except Exception:  # noqa: BLE001 - listHistory can name stale nodes
            continue
    # Fall back to the scene-wide cache nodes, but only accept one that
    # actually declares this cache name. Never guess: picking an arbitrary
    # cacheFile node would delete an unrelated cache, which is unrecoverable.
    candidates = [str(item) for item in (cmds.ls(type=CACHE_NODE_TYPE, long=True) or [])]
    matched: List[str] = []
    for node in candidates:
        try:
            declared = str(cmds.getAttr("{}.cacheName".format(node))).strip()
        except Exception:  # noqa: BLE001 - a listed node may not expose the plug
            continue
        if declared == file_name:
            matched.append(node)
    if len(matched) == 1:
        return matched[0]
    if not strict:
        return None
    if len(matched) > 1:
        raise NucleusContractError(
            "{} cacheFile nodes declare cacheName '{}' ({}); the cache to delete is ambiguous. "
            "Pass cache_nodes with the exact cacheFile node instead of scene_nodes.".format(
                len(matched), file_name, ", ".join(sorted(matched))
            )
        )
    if candidates:
        raise NucleusContractError(
            "No cacheFile node in {}'s history and none of the scene's {} cacheFile node(s) declares "
            "cacheName '{}'. Pass cache_nodes with the exact cacheFile node, or create the cache first.".format(
                shape, len(candidates), file_name
            )
        )
    raise NucleusContractError(
        "This scene has no cacheFile nodes and {}'s history holds none either; "
        "there is nothing to delete for '{}'.".format(shape, file_name)
    )


def resolve_frame_range(
    cmds: Any,
    start_frame: Optional[int],
    end_frame: Optional[int],
) -> Tuple[float, float]:
    """Resolve an explicit or scene-derived playback range for caching."""
    if start_frame is None or end_frame is None:
        scene_start = cmds.playbackOptions(query=True, minTime=True)
        scene_end = cmds.playbackOptions(query=True, maxTime=True)
    start = float(start_frame) if start_frame is not None else float(scene_start)
    end = float(end_frame) if end_frame is not None else float(scene_end)
    if end < start:
        raise NucleusContractError("end_frame ({}) must be >= start_frame ({})".format(end, start))
    return start, end


def _cache_file_paths(cache_path: str, cache_name: str) -> List[str]:
    """Return the exact on-disk paths Maya writes for one cache.

    Maya emits exactly two layouts for a cache called ``<name>``:

    * ``OneFile``         — ``<name>.mcx`` and ``<name>.xml``
    * ``OneFilePerFrame`` — ``<name>Frame<N>.mcx`` for each frame, plus ``<name>.xml``

    Matching these names exactly (rather than a ``<name>*`` prefix) matters:
    a prefix glob for ``hero`` would also match an unrelated ``heroine.mcx``
    and delete another cache's data. Glob metacharacters in the cache name are
    escaped, and a numeric wildcard matches only ``Frame<digits>``.
    """
    escaped = glob.escape(cache_name)
    patterns = (
        "{}.mcx".format(escaped),
        "{}.xml".format(escaped),
        "{}Frame[0-9]*.mcx".format(escaped),
    )
    found: List[str] = []
    for pattern in patterns:
        for path in glob.glob(os.path.join(glob.escape(cache_path), pattern)):
            if os.path.isfile(path) and path not in found:
                found.append(path)
    return sorted(found)


def _delete_cache_files(cmds: Any, node: str) -> List[str]:
    """Delete the on-disk files belonging to a ``cacheFile`` node.

    A ``cacheFile`` node stores its location in ``cachePath`` + ``cacheName``.
    Only the file names Maya actually writes are removed, so a cache whose
    name is a prefix of another cache cannot take the other one with it.
    Missing files are skipped so a partially-written cache cannot fail the
    delete.
    """
    try:
        cache_path = str(cmds.getAttr("{}.cachePath".format(node))).strip()
        cache_name = str(cmds.getAttr("{}.cacheName".format(node))).strip()
    except Exception:  # noqa: BLE001 - node may not expose the plugs
        return []
    if not cache_path or not cache_name:
        return []

    removed: List[str] = []
    for path in _cache_file_paths(cache_path, cache_name):
        try:
            os.remove(path)
        except OSError:  # noqa: BLE001 - best effort; report what we could not remove
            continue
        removed.append(path)
    return removed


def delete_cache(
    cmds: Any,
    cache_nodes: Optional[Sequence[str]] = None,
    scene_nodes: Optional[Sequence[str]] = None,
    delete_files: bool = False,
) -> Dict[str, Any]:
    """Detach and delete ``cacheFile`` nodes, optionally removing the files."""
    explicit = as_str_list(cache_nodes)
    derived: List[str] = []
    for node in as_str_list(scene_nodes):
        if not cmds.objExists(node):
            raise NucleusContractError("Node does not exist: {}".format(node))
        found = _find_cache_node(cmds, node, node.rsplit("|", 1)[-1].rsplit(":", 1)[-1], strict=True)
        if found:
            derived.append(found)

    targets: List[str] = []
    for node in explicit + derived:
        if node not in targets:
            targets.append(node)
    if not targets:
        raise NucleusContractError("No cacheFile nodes found; pass cache_nodes or scene_nodes")

    # Phase 1 - validate every target before the scene is touched.  Deleting a
    # cacheFile node is irreversible, so a list whose second entry is illegal
    # must not leave the first one already deleted: validate all, then delete.
    for node in targets:
        if not cmds.objExists(node):
            raise NucleusContractError("Cache node does not exist: {}".format(node))
        node_type = str(cmds.nodeType(node))
        if node_type != CACHE_NODE_TYPE:
            raise NucleusContractError(
                "{} is a {}; only {} nodes can be deleted. Pass cache_nodes with a "
                "cacheFile node, or scene_nodes with the geometry that carries the cache.".format(
                    node, node_type, CACHE_NODE_TYPE
                )
            )

    # Phase 2 - every target is a real cacheFile node, so it is safe to delete.
    removed_files: List[str] = []
    for node in targets:
        if delete_files:
            removed_files.extend(_delete_cache_files(cmds, node))
        cmds.delete(node)
    return {
        "deleted": targets,
        "count": len(targets),
        "delete_files": bool(delete_files),
        "removed_files": removed_files,
    }
