"""Unit tests for the Nucleus contract module (``dcc_mcp_maya.nucleus``).

These cover the typed boundary that the ``maya-dynamics`` nCloth / nRigid /
nConstraint / field / nCache tools are built on.  A fake ``cmds`` object keeps
the tests importable without a Maya interpreter.
"""

from __future__ import annotations

import pathlib
import sys
from contextlib import contextmanager

import pytest
from conftest import load_and_call

from dcc_mcp_maya import nucleus as nucleus_mod
from dcc_mcp_maya.nucleus import (
    CACHEABLE_NODE_TYPES,
    COMPOUND_ATTR_TYPES,
    DEFAULT_DIRECTION_FLAGS,
    FIELD_ATTRS,
    FIELD_COMMANDS,
    FIELD_COMPOUND_ATTRS,
    FIELD_CREATE_FLAGS,
    FIELD_DIRECTION_FLAGS,
    FIELD_POST_CREATE_ATTRS,
    FIELD_SUPPORTED_FLAGS,
    NCONSTRAINT_TYPES,
    NUCLEUS_ATTRS,
    NUCLEUS_COMPOUND_ATTRS,
    NUCLEUS_NODE_TYPE,
    NucleusContractError,
    _cache_file_paths,
    _find_cache_node,
    create_field,
    create_ncloth,
    create_nconstraint,
    create_nrigid,
    create_nucleus_solver,
    create_rigid_constraint,
    delete_cache,
    resolve_frame_range,
    set_field_properties,
    set_nucleus_properties,
    write_cache,
)


class _FakeCmds:
    """Minimal ``maya.cmds`` stand-in recording calls and node snapshots."""

    def __init__(self, existing=None, node_type="transform"):
        self.existing = dict(existing or {})
        self.node_type = node_type
        self.calls = []
        self._counts = {}
        self._after = {}

    # -- scene queries ------------------------------------------------------
    def objExists(self, node):
        return node in self.existing or node in self._after

    def nodeType(self, node):
        return self.existing.get(node) or self._after.get(node) or self.node_type

    def ls(self, **kwargs):
        node_type = kwargs.get("type")
        if node_type is None:
            return []
        pool = dict(self.existing)
        pool.update(self._after)
        return [name for name, kind in pool.items() if kind == node_type]

    def listRelatives(self, node, **_kwargs):
        return ["|{}Parent".format(node)]

    def listHistory(self, node):  # noqa: ARG002 - shape ignored in the fake
        return []

    def select(self, nodes, **_kwargs):
        self.calls.append(("select", list(nodes)))

    def playbackOptions(self, **kwargs):
        return 1.0 if kwargs.get("minTime") else 120.0

    def setAttr(self, plug, *args, **kwargs):
        self.calls.append(("setAttr", plug, args, kwargs))

    # -- factories ----------------------------------------------------------
    def _spawn(self, prefix, node_type, count=1):
        self._counts[prefix] = self._counts.get(prefix, 0) + 1
        name = "{}{}".format(prefix, self._counts[prefix])
        self._after[name] = node_type
        return name

    def nClothCreate(self, **kwargs):
        self.calls.append(("nClothCreate", kwargs))
        return self._spawn("nClothShape", "nCloth")

    def nRigid(self, node, **kwargs):
        self.calls.append(("nRigid", node, kwargs))
        return self._spawn("nRigidShape", "nRigid")

    def nConstraint(self, *args, **kwargs):
        self.calls.append(("nConstraint", args, kwargs))
        return self._spawn("dynamicConstraint", "dynamicConstraint")

    def nucleus(self, **kwargs):
        self.calls.append(("nucleus", kwargs))
        return self._spawn("nucleus", "nucleus")

    def rigidConstraint(self, *args, **kwargs):
        self.calls.append(("rigidConstraint", args, kwargs))
        return [self._spawn("rigidConstraint", "rigidConstraint")]

    def cacheFile(self, **kwargs):
        self.calls.append(("cacheFile", kwargs))
        return self._spawn("cacheFile", "cacheFile")

    def connectDynamic(self, nodes, **kwargs):
        self.calls.append(("connectDynamic", list(nodes), kwargs))

    def delete(self, node):
        self.calls.append(("delete", node))

    def _field(self, name, **kwargs):
        """Shared body for every dynamic field factory (air, drag, ...)."""
        self.calls.append((name, kwargs))
        return [self._spawn("{}Field".format(name), "{}Field".format(name))]

    def air(self, **kwargs):
        return self._field("air", **kwargs)

    def drag(self, **kwargs):
        return self._field("drag", **kwargs)

    def gravity(self, **kwargs):
        return self._field("gravity", **kwargs)

    def newton(self, **kwargs):
        return self._field("newton", **kwargs)

    def radial(self, **kwargs):
        return self._field("radial", **kwargs)

    def turbulence(self, **kwargs):
        return self._field("turbulence", **kwargs)

    def uniform(self, **kwargs):
        return self._field("uniform", **kwargs)

    def vortex(self, **kwargs):
        return self._field("vortex", **kwargs)

    def volumeAxis(self, **kwargs):
        return self._field("volumeAxis", **kwargs)


def _calls(cmds, name):
    return [call for call in cmds.calls if call[0] == name]


@contextmanager
def _patch_cache_files(removed):
    """Capture the paths ``_delete_cache_files`` removes."""
    original = nucleus_mod._delete_cache_files

    def _spy(cmds, node):
        paths = original(cmds, node)
        removed.extend(paths)
        return paths

    nucleus_mod._delete_cache_files = _spy
    try:
        yield
    finally:
        nucleus_mod._delete_cache_files = original


def _setattr(cmds):
    return {call[1]: call[2] for call in cmds.calls if call[0] == "setAttr"}


#: Flag that turns this file into the Maya-hosted drift checker.  See
#: :func:`_maya_check_main`.
MAYA_CHECK_ARGV = "--maya-field-table-check"


def _boot_maya_cmds():
    """Import and initialise a real ``maya.cmds``.

    The field commands (``air``, ``gravity``, ...) are not registered until
    Maya is initialised, so importing ``maya.cmds`` is not enough: under
    mayapy the flag tables stay empty until ``maya.standalone.initialize()``
    runs.

    Caller must run this in a child interpreter. Booting standalone mutates
    process-global state - ``is_gui_executable()`` starts reporting batch
    mode, which changes the dispatcher ``MayaMcpServer`` installs and breaks
    ``tests/test_server.py``.
    """
    import maya.cmds as cmds
    import maya.standalone

    maya.standalone.initialize()
    return cmds


def _maya_flag_names(cmds, command_name):
    """Long flag names Maya reports for a command, from ``cmds.help()``.

    ``cmds.help("gravity")`` prints lines like ``" -pv -perVertex  on|off"``;
    the long name is the second token. Only used by the Maya-hosted meta-test.
    """
    import re

    text = cmds.help(command_name, language="python") or ""
    return set(re.findall(r"^\s*-\w+\s+-(\w+)\s", text, re.M))


# ---------------------------------------------------------------------------
# nCloth
# ---------------------------------------------------------------------------


def test_create_ncloth_creates_one_node_per_mesh():
    cmds = _FakeCmds(existing={"pPlane1": "mesh", "pPlane2": "mesh"})

    result = create_ncloth(cmds, objects=["pPlane1", "pPlane2"])

    assert result["ncloth_nodes"] == ["nClothShape1", "nClothShape2"]
    assert [call[1] for call in _calls(cmds, "select")] == [["pPlane1"], ["pPlane2"]]
    assert len(_calls(cmds, "nClothCreate")) == 2


def test_create_ncloth_applies_properties_to_each_shape():
    cmds = _FakeCmds(existing={"pPlane1": "mesh"}, node_type="mesh")

    result = create_ncloth(cmds, objects=["pPlane1"], properties={"thickness": 0.05, "stretch_resistance": 20.0})

    assert result["created"][0]["properties"] == {"thickness": 0.05, "stretch_resistance": 20.0}
    applied = _setattr(cmds)
    assert applied["nClothShape1.thickness"] == (0.05,)
    assert applied["nClothShape1.stretchResistance"] == (20.0,)


def test_create_ncloth_suffixes_names_for_multiple_targets():
    cmds = _FakeCmds(existing={"pPlane1": "mesh", "pPlane2": "mesh"})

    create_ncloth(cmds, objects=["pPlane1", "pPlane2"], name="cloth")

    names = [call[1].get("name") for call in _calls(cmds, "nClothCreate")]
    assert names == ["cloth_01", "cloth_02"]


def test_create_ncloth_rejects_missing_node():
    with pytest.raises(NucleusContractError, match="Nodes do not exist"):
        create_ncloth(_FakeCmds(), objects=["ghost"])


def test_create_ncloth_rejects_unknown_property():
    cmds = _FakeCmds(existing={"pPlane1": "mesh"})
    with pytest.raises(NucleusContractError, match="Unsupported attribute"):
        create_ncloth(cmds, objects=["pPlane1"], properties={"not_an_attr": 1.0})


# ---------------------------------------------------------------------------
# nRigid
# ---------------------------------------------------------------------------


def test_create_nrigid_makes_passive_colliders():
    cmds = _FakeCmds(existing={"pCube1": "mesh"})

    result = create_nrigid(cmds, objects=["pCube1"], name="collider", properties={"thickness": 0.1})

    assert result["nrigid_nodes"] == ["nRigidShape1"]
    assert _calls(cmds, "nRigid")[0][2]["name"] == "collider"
    assert _setattr(cmds)["nRigidShape1.thickness"] == (0.1,)


# ---------------------------------------------------------------------------
# nConstraint
# ---------------------------------------------------------------------------


def test_create_nconstraint_passes_driver_last():
    cmds = _FakeCmds(existing={"clothShape": "nCloth", "collider": "mesh"})

    result = create_nconstraint(cmds, objects=["clothShape"], target="collider", constraint_type="weld")

    assert result["constraint_type"] == "weld"
    assert _calls(cmds, "nConstraint")[0][1] == ("clothShape", "collider")
    assert _calls(cmds, "nConstraint")[0][2]["type"] == "weld"


def test_create_nconstraint_rejects_unknown_type():
    with pytest.raises(NucleusContractError, match="constraint_type must be one of"):
        create_nconstraint(_FakeCmds(), objects=["clothShape"], constraint_type="glue")


def test_create_nconstraint_requires_driven_nodes():
    cmds = _FakeCmds()
    cmds.ls = lambda **_kwargs: []
    with pytest.raises(NucleusContractError, match="objects \\(or a selection\\) is required"):
        create_nconstraint(cmds, objects=None)


def test_nconstraint_types_match_maya_surface():
    assert "attractToMatchingMesh" in NCONSTRAINT_TYPES
    assert "excludeCollisionPairs" in NCONSTRAINT_TYPES


# ---------------------------------------------------------------------------
# Nucleus solver
# ---------------------------------------------------------------------------


def test_create_nucleus_solver_applies_global_settings():
    cmds = _FakeCmds()

    result = create_nucleus_solver(cmds, name="solverA", properties={"substeps": 4, "space_scale": 0.01})

    assert result["nucleus"] == "nucleus1"
    assert _calls(cmds, "nucleus")[0][1]["name"] == "solverA"
    assert _setattr(cmds)["nucleus1.substeps"] == (4,)


def test_set_nucleus_properties_auto_detects_solver():
    cmds = _FakeCmds(existing={"nucleus1": "nucleus"})

    result = set_nucleus_properties(cmds, properties={"gravity": 9.81})

    assert result["nucleus"] == "nucleus1"


def test_set_nucleus_properties_requires_a_solver():
    with pytest.raises(NucleusContractError, match="No nucleus solver"):
        set_nucleus_properties(_FakeCmds(), properties={"gravity": 9.81})


def test_nucleus_gravity_direction_uses_double3():
    cmds = _FakeCmds(existing={"nucleus1": "nucleus"})

    set_nucleus_properties(cmds, solver="nucleus1", properties={"gravity_direction": [0.0, -1.0, 0.0]})

    call = [item for item in cmds.calls if item[0] == "setAttr" and item[1].endswith("gravityDirection")][0]
    assert call[2] == (0.0, -1.0, 0.0)
    assert call[3] == {"type": "double3"}


def test_nucleus_attr_map_exposes_snake_case_keys():
    assert NUCLEUS_ATTRS["max_collision_iterations"] == "maxCollisionIterations"
    assert NUCLEUS_ATTRS["space_scale"] == "spaceScale"


# ---------------------------------------------------------------------------
# Dynamic fields
# ---------------------------------------------------------------------------


def test_create_field_translates_direction_into_component_flags():
    cmds = _FakeCmds()

    result = create_field(cmds, field_type="gravity", magnitude=9.8, direction=[0.0, -1.0, 0.0])

    assert result["field_type"] == "gravity"
    kwargs = _calls(cmds, "gravity")[0][1]
    assert kwargs["magnitude"] == 9.8
    assert (kwargs["directionX"], kwargs["directionY"], kwargs["directionZ"]) == (0.0, -1.0, 0.0)


def test_create_field_connects_targets_when_requested():
    cmds = _FakeCmds(existing={"pPlane1": "mesh"})

    result = create_field(cmds, field_type="air", targets=["pPlane1"])

    assert result["targets"] == ["pPlane1"]
    kwargs = _calls(cmds, "connectDynamic")[0][2]
    assert kwargs["fields"] == "airField1"
    assert kwargs["delete"] is False


def test_create_field_omits_connection_when_disabled():
    cmds = _FakeCmds(existing={"pPlane1": "mesh"})

    create_field(cmds, field_type="air", targets=["pPlane1"], connect=False)

    assert _calls(cmds, "connectDynamic") == []


def test_create_field_rejects_flag_not_supported_by_that_field_type():
    cmds = _FakeCmds()
    with pytest.raises(NucleusContractError, match="gravity field does not support: frequency"):
        create_field(cmds, field_type="gravity", frequency=2.0)


def test_create_field_rejects_unknown_field_type():
    with pytest.raises(NucleusContractError, match="field_type must be one of"):
        create_field(_FakeCmds(), field_type="magnet")


def test_create_field_sets_translate_when_position_given():
    cmds = _FakeCmds()

    create_field(cmds, field_type="turbulence", position=[1.0, 2.0, 3.0])

    translate = [item for item in cmds.calls if item[0] == "setAttr" and item[1].endswith(".translate")]
    assert translate[0][2] == (1.0, 2.0, 3.0)


def test_field_commands_cover_the_full_create_surface():
    assert set(FIELD_COMMANDS) == {
        "air",
        "drag",
        "gravity",
        "newton",
        "radial",
        "turbulence",
        "uniform",
        "vortex",
        "volume_axis",
    }
    assert FIELD_COMMANDS["volume_axis"] == "volumeAxis"


def test_field_flag_whitelist_covers_every_field_type():
    """The whitelist is the only thing standing between an agent's settings
    and ``cmds.<field>(**flags)``, so it must cover every field type.

    A field type missing from the whitelist would reject *all* settings
    (``FIELD_SUPPORTED_FLAGS.get`` falls back to ``()``) - fail loudly here
    instead of shipping a tool whose every flag errors.
    """
    assert set(FIELD_SUPPORTED_FLAGS) == set(FIELD_COMMANDS)
    for field_type, flags in FIELD_SUPPORTED_FLAGS.items():
        assert flags, "{} whitelists no flags at all".format(field_type)
        assert len(set(flags)) == len(flags), "{} whitelists duplicates".format(field_type)


def test_field_flag_whitelist_only_names_known_settings():
    """Every whitelisted setting must resolve to a create flag.

    ``direction`` expands into component flags and is handled separately; the
    rest must be in :data:`FIELD_CREATE_FLAGS` or the post-create map.
    """
    for field_type, flags in FIELD_SUPPORTED_FLAGS.items():
        for key in flags:
            assert key == "direction" or key in FIELD_CREATE_FLAGS or key in FIELD_POST_CREATE_ATTRS, (
                "{} whitelists '{}', which maps to no create flag".format(field_type, key)
            )


def test_field_create_flags_are_a_subset_of_the_property_vocabulary():
    """The create surface and the edit surface must use the same key names.

    Agents pass snake_case settings to both ``create_dynamic_field`` and
    ``set_field_properties``; a key that exists on one side only is confusing
    and is usually a typo. ``section_radius`` is the one deliberate difference:
    the create flag is ``-torusSectionRadius`` while the node exposes
    ``sectionRadius``.
    """
    create_keys = set(FIELD_CREATE_FLAGS) | set(FIELD_POST_CREATE_ATTRS)
    assert create_keys <= set(FIELD_ATTRS)


def test_field_attrs_and_create_flags_differ_only_where_maya_does():
    """The two maps must agree except for the names Maya itself splits.

    Most settings carry the same name on the command and on the node. A new
    divergence is either a typo or a Maya quirk that needs a comment, so pin
    the known exceptions.
    """
    known_splits = {"apply_per_vertex", "section_radius"}
    diverged = {
        key for key in set(FIELD_CREATE_FLAGS) & set(FIELD_ATTRS) if FIELD_CREATE_FLAGS[key] != FIELD_ATTRS[key]
    }
    assert diverged == known_splits


def test_field_direction_flags_are_per_field_type():
    """``vortex`` is the one field command that names its axis flags differently."""
    assert FIELD_DIRECTION_FLAGS["vortex"] == ("axisX", "axisY", "axisZ")
    for field_type in FIELD_DIRECTION_FLAGS:
        assert field_type in FIELD_COMMANDS, "direction override for an unknown field type"
        assert len(FIELD_DIRECTION_FLAGS[field_type]) == 3
    assert len(DEFAULT_DIRECTION_FLAGS) == 3


def test_create_field_uses_per_field_direction_flags():
    """``vortex`` must emit ``axis*``; real ``cmds.vortex`` has no ``direction*``."""
    cmds = _FakeCmds()

    create_field(cmds, field_type="vortex", direction=[0.0, 1.0, 0.0])

    kwargs = _calls(cmds, "vortex")[0][1]
    assert (kwargs["axisX"], kwargs["axisY"], kwargs["axisZ"]) == (0.0, 1.0, 0.0)
    assert "directionX" not in kwargs


def test_create_field_uses_pervertex_flag_not_the_node_attribute():
    """Regression: ``applyPerVertex`` is a node attribute, not a create flag.

    ``cmds.gravity(applyPerVertex=True)`` raises ``TypeError: invalid flag`` on
    real Maya. The fake ``cmds`` accepted it, so only this whitelist keeps the
    two vocabularies apart.
    """
    cmds = _FakeCmds()

    create_field(cmds, field_type="gravity", apply_per_vertex=True)

    kwargs = _calls(cmds, "gravity")[0][1]
    assert kwargs["perVertex"] is True
    assert "applyPerVertex" not in kwargs


def test_create_field_applies_node_only_settings_after_the_node_exists():
    """``trap_inside`` / ``turbulence_frequency`` are attributes, not flags."""
    cmds = _FakeCmds()

    create_field(cmds, field_type="volume_axis", trap_inside=False, turbulence_frequency=[2.0, 2.0, 2.0])

    kwargs = _calls(cmds, "volumeAxis")[0][1]
    assert "trapInside" not in kwargs
    assert "turbulenceFrequency" not in kwargs
    applied = _setattr(cmds)
    assert applied["volumeAxisField1.trapInside"] == (False,)
    assert applied["volumeAxisField1.turbulenceFrequency"] == (2.0, 2.0, 2.0)


def test_create_field_explains_retired_settings():
    """A setting no Maya build exposes gets guidance, not a bare rejection.

    The wording matters: the generic "does not support" message would just
    list the whitelist, which does not say why the setting is gone.
    """
    with pytest.raises(NucleusContractError, match="no Maya field command") as excinfo:
        create_field(_FakeCmds(), field_type="volume_axis", directional_strength=0.5)

    assert "directional_speed" in str(excinfo.value)


def test_create_field_rejects_scalar_value_for_a_compound_attr():
    """``turbulenceFrequency`` is a double3; a scalar fails with an opaque Maya error."""
    with pytest.raises(NucleusContractError, match="turbulence_frequency expects a 3-element"):
        create_field(_FakeCmds(), field_type="volume_axis", turbulence_frequency=2.0)


def test_create_field_writes_compound_attrs_with_all_components():
    """A 3-element value must reach setAttr as a double3 with three components."""
    cmds = _FakeCmds()

    create_field(cmds, field_type="volume_axis", turbulence_frequency=[1.0, 2.0, 3.0])

    applied = [call for call in cmds.calls if call[0] == "setAttr" and "turbulenceFrequency" in call[1]]
    assert applied[0][2] == (1.0, 2.0, 3.0)
    assert applied[0][3] == {"type": "double3"}


def test_create_field_rejects_a_short_compound_list_before_creating_the_node():
    """A 2-element value must not leave an orphan field node behind.

    ``create_field`` validates the whole payload before calling the factory,
    the same validate-then-apply rule the nCache delete path follows - an
    orphan node is invisible to the caller but pollutes every later scene
    query.
    """
    cmds = _FakeCmds()

    with pytest.raises(NucleusContractError, match=r"turbulence_frequency expects a 3-element \[x, y, z\] list, got 2"):
        create_field(cmds, field_type="volume_axis", turbulence_frequency=[1.0, 2.0])

    assert _calls(cmds, "volumeAxis") == [], "a rejected payload must not reach the field factory"
    assert cmds._after == {}, "a rejected payload must not create nodes"


def test_create_field_rejects_a_scalar_direction():
    """``direction`` is a compound too; a scalar used to raise a bare TypeError."""
    with pytest.raises(NucleusContractError, match="direction expects a 3-element"):
        create_field(_FakeCmds(), field_type="gravity", direction=1.0)


def test_compound_attr_tables_only_name_known_settings():
    """The compound lists must name keys the attribute maps actually expose.

    A typo here would silently disable the guard for that key.
    """
    for key in FIELD_COMPOUND_ATTRS:
        assert key in FIELD_ATTRS, "compound field setting '{}' is not in FIELD_ATTRS".format(key)
    for key in NUCLEUS_COMPOUND_ATTRS:
        assert key in NUCLEUS_ATTRS, "compound nucleus setting '{}' is not in NUCLEUS_ATTRS".format(key)


def _collect_maya_table_errors(cmds):
    """Return a list of drift descriptions; empty means Maya agrees with us.

    Runs inside the child interpreter spawned by
    :func:`test_field_tables_match_a_real_maya`.
    """
    errors = []

    # 1. Every whitelisted create flag must exist on its command.
    for field_type, settings in sorted(FIELD_SUPPORTED_FLAGS.items()):
        command_name = FIELD_COMMANDS[field_type]
        if getattr(cmds, command_name, None) is None:
            errors.append("maya.cmds.{} is missing".format(command_name))
            continue

        flags = _maya_flag_names(cmds, command_name)
        for key in settings:
            if key in FIELD_POST_CREATE_ATTRS:
                # Deliberately not a create flag - applied with setAttr after.
                continue
            if key == "direction":
                expected = list(FIELD_DIRECTION_FLAGS.get(field_type, DEFAULT_DIRECTION_FLAGS))
            else:
                expected = [FIELD_CREATE_FLAGS[key]]
            for flag_name in expected:
                if flag_name not in flags:
                    errors.append(
                        "cmds.{} has no -{} flag (whitelisted for '{}')".format(command_name, flag_name, field_type)
                    )

    # 2. Every FIELD_ATTRS entry must exist on some field node. ``vortex``
    #    exposes no directionX/Y/Z, so compare against the union of the family.
    available = set()
    for _field_type, command_name in sorted(FIELD_COMMANDS.items()):
        command = getattr(cmds, command_name, None)
        if command is None:
            continue
        node = command()
        try:
            attrs = cmds.listAttr(node) or []
            available.update(attrs)
            errors.extend(_maya_compound_drift(cmds, node, attrs, FIELD_ATTRS, FIELD_COMPOUND_ATTRS, _field_type))
        finally:
            cmds.delete(node)

    for key, attr in sorted(FIELD_ATTRS.items()):
        if key in ("direction", "speed", "phase"):
            continue
        if attr not in available:
            errors.append("FIELD_ATTRS names attribute '{}' ({}) no field node exposes".format(attr, key))

    # 3. The nucleus solver compounds (gravity / wind direction are float3).
    solver = cmds.createNode(NUCLEUS_NODE_TYPE)
    try:
        errors.extend(
            _maya_compound_drift(
                cmds,
                solver,
                cmds.listAttr(solver) or [],
                NUCLEUS_ATTRS,
                NUCLEUS_COMPOUND_ATTRS,
                NUCLEUS_NODE_TYPE,
            )
        )
    finally:
        cmds.delete(solver)

    return errors


def _maya_compound_drift(cmds, node, attrs, attr_map, compound, label):
    """Describe every compound / scalar mismatch between a table and Maya.

    Only attributes the node actually exposes are checked - ``vortex`` has no
    ``direction``, so it is simply skipped.  Both directions matter: an
    unmarked compound re-opens the opaque "error reading data element number 2"
    the guard exists to prevent, and a wrongly marked scalar rejects a value
    Maya would have accepted.
    """
    drift = []
    if isinstance(node, (list, tuple)):
        # A field factory returns [fieldShape] rather than a plain name.
        node = node[0]
    for key, attr in sorted(attr_map.items()):
        if attr not in attrs:
            continue
        reported = cmds.getAttr("{}.{}".format(node, attr), type=True)
        is_compound = reported in COMPOUND_ATTR_TYPES
        if is_compound and key not in compound:
            drift.append(
                "{}: '{}' ({}) is a {} in Maya but is not in the compound list".format(label, attr, key, reported)
            )
        if key in compound and not is_compound:
            drift.append("{}: '{}' ({}) is marked compound but Maya reports {}".format(label, attr, key, reported))
    return drift


def _maya_check_main():
    """Child-interpreter entry point; print drift and return an exit code."""
    try:
        cmds = _boot_maya_cmds()
    except Exception as exc:  # noqa: BLE001 - report and let the parent decide
        print("MAYA_BOOT_FAILED: {}".format(exc))
        return 1

    if getattr(cmds, "air", None) is None:
        print("MAYA_BOOT_FAILED: field commands are not registered")
        return 1

    errors = _collect_maya_table_errors(cmds)
    for line in errors:
        print("DRIFT: {}".format(line))
    return 1 if errors else 0


def test_field_tables_match_a_real_maya():
    """Meta-test: the flag and attribute tables must match real Maya.

    Unit tests run against a fake ``cmds`` that swallows every keyword, so they
    cannot catch a flag Maya rejects - five whitelisted flags were wrong before
    this check existed. It runs in the mayapy CI job, where a real Maya is
    available.

    The check runs in a child interpreter because booting
    ``maya.standalone`` flips ``is_gui_executable()`` to batch mode for the
    whole process, which changes the dispatcher ``MayaMcpServer`` installs and
    breaks ``tests/test_server.py``.
    """
    import subprocess

    try:
        import importlib.util

        if importlib.util.find_spec("maya.cmds") is None:
            pytest.skip("maya.cmds is not importable in this interpreter")
    except (ImportError, ValueError):
        pytest.skip("maya.cmds is not importable in this interpreter")

    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve()), MAYA_CHECK_ARGV],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")

    # Deliberately no skip based on the child's output: a child that could not
    # boot must fail, otherwise a broken Maya install silently turns the guard
    # into a no-op. The only skip is the parent's own import check above.
    assert result.returncode == 0, "Maya disagrees with the field tables:\n" + output.strip()


def test_set_field_properties_edits_only_supplied_values():
    cmds = _FakeCmds(existing={"airField1": "airField"})

    result = set_field_properties(cmds, fields=["airField1"], properties={"magnitude": 3.0, "attenuation": 0.5})

    assert result["count"] == 1
    applied = _setattr(cmds)
    assert applied["airField1.magnitude"] == (3.0,)
    assert applied["airField1.attenuation"] == (0.5,)


def test_set_field_properties_rejects_empty_payload():
    with pytest.raises(NucleusContractError, match="at least one attribute"):
        set_field_properties(_FakeCmds(), fields=["airField1"], properties={})


def test_set_field_properties_rejects_scalar_for_a_compound_attr():
    """The edit path must guard compounds the way the create path does.

    Before this guard, ``turbulence_frequency=2.0`` reached Maya as a bare
    ``setAttr("...turbulenceFrequency", 2.0)`` and failed with an opaque
    "error reading data element number 2".
    """
    cmds = _FakeCmds(existing={"volumeAxisField1": "volumeAxisField"})

    with pytest.raises(NucleusContractError, match="turbulence_frequency expects a 3-element"):
        set_field_properties(cmds, fields=["volumeAxisField1"], properties={"turbulence_frequency": 2.0})

    assert _setattr(cmds) == {}, "a rejected payload must not touch the node"


def test_set_field_properties_rejects_a_short_compound_list():
    cmds = _FakeCmds(existing={"volumeAxisField1": "volumeAxisField"})

    with pytest.raises(NucleusContractError, match=r"turbulence_frequency expects a 3-element \[x, y, z\] list, got 2"):
        set_field_properties(cmds, fields=["volumeAxisField1"], properties={"turbulence_frequency": [1.0, 2.0]})

    assert _setattr(cmds) == {}


def test_set_field_properties_rejects_a_scalar_direction():
    """``direction`` is a compound on every field that exposes it."""
    cmds = _FakeCmds(existing={"airField1": "airField"})

    with pytest.raises(NucleusContractError, match="direction expects a 3-element"):
        set_field_properties(cmds, fields=["airField1"], properties={"direction": 1.0})

    assert _setattr(cmds) == {}


def test_set_field_properties_validates_every_value_before_editing():
    """One bad value must not leave the field half-edited."""
    cmds = _FakeCmds(existing={"volumeAxisField1": "volumeAxisField"})

    with pytest.raises(NucleusContractError, match="turbulence_frequency"):
        set_field_properties(
            cmds,
            fields=["volumeAxisField1"],
            properties={"magnitude": 3.0, "turbulence_frequency": 2.0},
        )

    assert _setattr(cmds) == {}, "magnitude must not be applied before the payload is accepted"


def test_set_nucleus_properties_rejects_a_scalar_gravity_direction():
    """``gravityDirection`` is a float3; a scalar hits the same opaque error."""
    cmds = _FakeCmds(existing={"nucleus1": "nucleus"})

    with pytest.raises(NucleusContractError, match="gravity_direction expects a 3-element"):
        set_nucleus_properties(cmds, solver="nucleus1", properties={"gravity_direction": 9.8})

    assert _setattr(cmds) == {}


# ---------------------------------------------------------------------------
# Rigid constraints
# ---------------------------------------------------------------------------


def test_create_rigid_constraint_uses_hinge_type():
    cmds = _FakeCmds(existing={"rb1": "rigidBody", "rb2": "rigidBody"})

    result = create_rigid_constraint(cmds, objects=["rb1", "rb2"], constraint_type="hinge")

    assert result["constraint_type"] == "hinge"
    assert _calls(cmds, "rigidConstraint")[0][1] == ("rb1", "rb2")


def test_create_rigid_constraint_rejects_unknown_type():
    cmds = _FakeCmds(existing={"rb1": "rigidBody"})
    with pytest.raises(NucleusContractError, match="constraint_type must be one of"):
        create_rigid_constraint(cmds, objects=["rb1"], constraint_type="rope")


# ---------------------------------------------------------------------------
# nCache
# ---------------------------------------------------------------------------


def test_write_cache_uses_scene_range_when_frames_omitted():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})

    result = write_cache(cmds, nodes=["nClothShape1"], directory="/tmp/cache", file_name="cloth")

    assert result["frame_range"] == [1.0, 120.0]
    kwargs = _calls(cmds, "cacheFile")[0][1]
    assert kwargs["fileName"] == "cloth"
    assert kwargs["directory"] == "/tmp/cache"
    assert kwargs["format"] == "OneFile"
    assert kwargs["startTime"] == 1.0
    assert kwargs["endTime"] == 120.0
    # A real cacheFile node must be created, otherwise the cache is written
    # but never drives the geometry back.
    assert kwargs["createCacheNode"] is True


def test_write_cache_honours_explicit_frames_and_formats():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})

    result = write_cache(
        cmds,
        nodes=["nClothShape1"],
        directory="/tmp/cache",
        start_frame=10,
        end_frame=50,
        cache_format="OneFilePerFrame",
        data_format="mcx",
        world_space=True,
    )

    assert result["frame_range"] == [10.0, 50.0]
    kwargs = _calls(cmds, "cacheFile")[0][1]
    assert kwargs["format"] == "OneFilePerFrame"
    # Maya's real flag is -cacheFormat; -dataFormat does not exist.
    assert kwargs["cacheFormat"] == "mcx"
    assert "dataFormat" not in kwargs
    assert kwargs["worldSpace"] is True


def test_write_cache_requires_a_directory():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})
    with pytest.raises(NucleusContractError, match="directory is required"):
        write_cache(cmds, nodes=["nClothShape1"], directory="")


def test_write_cache_rejects_inverted_frame_range():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})
    with pytest.raises(NucleusContractError, match="end_frame .* must be >= start_frame"):
        write_cache(cmds, nodes=["nClothShape1"], directory="/tmp/cache", start_frame=50, end_frame=10)


def test_write_cache_rejects_unknown_cache_format():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})
    with pytest.raises(NucleusContractError, match="cache_format must be one of"):
        write_cache(cmds, nodes=["nClothShape1"], directory="/tmp/cache", cache_format="abc")


def test_write_cache_reports_cancellation_between_nodes():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth", "nClothShape2": "nCloth"})
    seen = []

    write_cache(
        cmds, nodes=["nClothShape1", "nClothShape2"], directory="/tmp/cache", on_cancelled=lambda: seen.append(1)
    )

    assert len(seen) == 2


def test_resolve_frame_range_prefers_explicit_values():
    cmds = _FakeCmds()
    assert resolve_frame_range(cmds, 5, 9) == (5.0, 9.0)


def test_cacheable_types_are_restricted_to_output_geometry():
    assert "nCloth" in CACHEABLE_NODE_TYPES
    assert "transform" not in CACHEABLE_NODE_TYPES


def test_delete_cache_detaches_nodes_without_touching_files():
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})

    result = delete_cache(cmds, cache_nodes=["cacheFile1"])

    assert result["deleted"] == ["cacheFile1"]
    assert _calls(cmds, "delete") == [("delete", "cacheFile1")]
    assert result["delete_files"] is False
    assert result["removed_files"] == []


def test_delete_cache_can_remove_files_too():
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})
    files = []

    with _patch_cache_files(files):
        result = delete_cache(cmds, cache_nodes=["cacheFile1"], delete_files=True)

    assert result["delete_files"] is True
    # Node is still removed even when delete_files is set.
    assert _calls(cmds, "delete") == [("delete", "cacheFile1")]
    assert result["removed_files"] == files


def test_delete_cache_requires_a_target():
    with pytest.raises(NucleusContractError, match="No cacheFile nodes found"):
        delete_cache(_FakeCmds())


def test_delete_cache_removes_onefile_and_perframe_files(tmp_path):
    """Real-filesystem check: both Maya cache layouts are removed.

    The neighbour cache deliberately SHARES THE PREFIX ("heroine" starts with
    "hero") so a naive prefix glob would silently delete it.
    """
    for name in (
        "hero.mcx",
        "hero.xml",
        "heroFrame1.mcx",
        "heroFrame2.mcx",
        "heroine.mcx",
        "heroine.xml",
        "heroineFrame1.mcx",
        "hero_v2.mcx",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})
    cmds.getAttr = lambda plug: str(tmp_path) + "/" if plug.endswith("cachePath") else "hero"

    result = delete_cache(cmds, cache_nodes=["cacheFile1"], delete_files=True)

    assert result["delete_files"] is True
    removed = {pathlib.Path(p).name for p in result["removed_files"]}
    assert removed == {"hero.mcx", "hero.xml", "heroFrame1.mcx", "heroFrame2.mcx"}
    # Same-prefix neighbours must survive.
    for survivor in ("heroine.mcx", "heroine.xml", "heroineFrame1.mcx", "hero_v2.mcx"):
        assert (tmp_path / survivor).exists(), survivor


def test_delete_cache_keeps_files_when_not_requested(tmp_path):
    (tmp_path / "hero.mcx").write_text("x", encoding="utf-8")
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})
    cmds.getAttr = lambda plug: str(tmp_path) + "/" if plug.endswith("cachePath") else "hero"

    delete_cache(cmds, cache_nodes=["cacheFile1"])

    assert (tmp_path / "hero.mcx").exists()


def test_delete_cache_does_not_touch_same_prefix_caches(tmp_path):
    """A cache named `hero` must not delete an unrelated `heroine` cache."""
    for name in (
        "hero.mcx",
        "hero.xml",
        "heroFrame1.mcx",
        "heroFrame2.mcx",
        # Same prefix, different cache - must survive.
        "heroine.mcx",
        "heroine.xml",
        "heroineFrame1.mcx",
        "heroBackup.mcx",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})
    cmds.getAttr = lambda plug: str(tmp_path) + "/" if plug.endswith("cachePath") else "hero"

    result = delete_cache(cmds, cache_nodes=["cacheFile1"], delete_files=True)

    removed = {pathlib.Path(p).name for p in result["removed_files"]}
    assert removed == {"hero.mcx", "hero.xml", "heroFrame1.mcx", "heroFrame2.mcx"}
    for survivor in ("heroine.mcx", "heroine.xml", "heroineFrame1.mcx", "heroBackup.mcx"):
        assert (tmp_path / survivor).exists(), survivor


def test_cache_file_paths_escapes_glob_metacharacters(tmp_path):
    """Cache names containing glob wildcards must be matched literally."""
    for name in ("a[1].mcx", "a[1].xml", "a1.mcx"):
        (tmp_path / name).write_text("x", encoding="utf-8")

    paths = _cache_file_paths(str(tmp_path), "a[1]")

    assert {pathlib.Path(p).name for p in paths} == {"a[1].mcx", "a[1].xml"}


def test_delete_cache_refuses_non_cachefile_nodes():
    """Deleting a mesh transform by mistake must fail, not delete the mesh."""
    cmds = _FakeCmds(existing={"pCube1": "mesh"})

    with pytest.raises(NucleusContractError, match="pCube1 is a mesh"):
        delete_cache(cmds, cache_nodes=["pCube1"])

    assert _calls(cmds, "delete") == []


def test_delete_cache_reports_actual_type_when_refusing():
    cmds = _FakeCmds(existing={"group1": "transform"})

    with pytest.raises(NucleusContractError, match="is a transform.*only cacheFile nodes"):
        delete_cache(cmds, cache_nodes=["group1"], delete_files=True)

    assert _calls(cmds, "delete") == []


def test_find_cache_node_does_not_guess_when_scene_has_other_caches():
    """Never delete an unrelated cacheFile node just because one exists."""
    cmds = _FakeCmds(existing={"pCube1": "mesh"})
    cmds.listHistory = lambda node: []  # no cache in this node's history

    def _ls(**kwargs):
        return ["cacheFile1", "cacheFile2"] if kwargs.get("type") == "cacheFile" else []

    cmds.ls = _ls
    cmds.getAttr = lambda plug: "other" if plug.startswith("cacheFile") else None

    assert _find_cache_node(cmds, "pCube1", "pCube1") is None
    with pytest.raises(NucleusContractError, match="No cacheFile node in pCube1's history"):
        delete_cache(cmds, scene_nodes=["pCube1"])


def test_delete_cache_names_the_ambiguous_caches_instead_of_blaming_the_caller():
    """Two caches sharing a cacheName must not report "no cacheFile nodes".

    The agent did pass ``scene_nodes`` and the scene plainly does hold caches,
    so telling it to "pass cache_nodes or scene_nodes" sends it in a circle.
    """
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})
    cmds.listHistory = lambda node: []

    def _ls(**kwargs):
        return ["heroCache1", "heroCache2"] if kwargs.get("type") == "cacheFile" else []

    cmds.ls = _ls
    cmds.getAttr = lambda plug: "nClothShape1" if plug.startswith("heroCache") else None

    with pytest.raises(NucleusContractError, match="2 cacheFile nodes declare cacheName 'nClothShape1'"):
        delete_cache(cmds, scene_nodes=["nClothShape1"])

    assert _calls(cmds, "delete") == []


def test_delete_cache_reports_an_empty_scene_as_such():
    """No caches anywhere is a different story from "I could not tell which"."""
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})
    cmds.listHistory = lambda node: []
    cmds.ls = lambda **kwargs: []

    with pytest.raises(NucleusContractError, match="This scene has no cacheFile nodes"):
        delete_cache(cmds, scene_nodes=["nClothShape1"])


def test_delete_cache_validates_every_target_before_deleting_any():
    """A partially-invalid target list must not delete anything.

    Deleting one legal cache and then failing on an illegal one is a partial
    success the caller cannot undo, so validation has to finish first.
    """
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile", "pCube1": "mesh"})

    with pytest.raises(NucleusContractError, match="pCube1 is a mesh"):
        delete_cache(cmds, cache_nodes=["cacheFile1", "pCube1"])

    assert _calls(cmds, "delete") == []


def test_find_cache_node_matches_by_declared_cache_name():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})
    cmds.listHistory = lambda node: []

    def _ls(**kwargs):
        return ["heroCache1", "heroineCache1"] if kwargs.get("type") == "cacheFile" else []

    cmds.ls = _ls
    names = {"heroCache1.cacheName": "hero", "heroineCache1.cacheName": "heroine"}
    cmds.getAttr = lambda plug: names.get(plug)

    # Exactly one node declares the name -> resolved; the look-alike is ignored.
    assert _find_cache_node(cmds, "nClothShape1", "hero") == "heroCache1"


def test_delete_cache_tolerates_nodes_without_cache_plugs():
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})

    def _boom(plug):  # noqa: ARG001 - simulate a node without cache plugs
        raise RuntimeError("no such attr")

    cmds.getAttr = _boom

    result = delete_cache(cmds, cache_nodes=["cacheFile1"], delete_files=True)

    assert result["removed_files"] == []
    assert _calls(cmds, "delete") == [("delete", "cacheFile1")]


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


def test_skill_create_ncloth_returns_success_envelope():
    cmds = _FakeCmds(existing={"pPlane1": "mesh"})

    result = load_and_call(
        "maya-dynamics/scripts/create_ncloth.py",
        cmds,
        "main",
        objects=["pPlane1"],
        thickness=0.05,
    )

    assert result["success"] is True, result
    assert result["context"]["ncloth_nodes"] == ["nClothShape1"]


def test_skill_create_ncloth_reports_missing_objects():
    result = load_and_call("maya-dynamics/scripts/create_ncloth.py", _FakeCmds(), "main", objects=["ghost"])

    assert result["success"] is False


def test_skill_create_nucleus_returns_solver():
    result = load_and_call(
        "maya-dynamics/scripts/create_nucleus.py",
        _FakeCmds(),
        "main",
        name="solverA",
        substeps=3,
    )

    assert result["success"] is True, result
    assert result["context"]["nucleus"] == "nucleus1"


def test_skill_create_dynamic_field_rejects_unsupported_flag():
    result = load_and_call(
        "maya-dynamics/scripts/create_dynamic_field.py",
        _FakeCmds(),
        "main",
        field_type="gravity",
        frequency=2.0,
    )

    assert result["success"] is False


def test_skill_create_ncache_writes_per_node():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})

    result = load_and_call(
        "maya-dynamics/scripts/create_ncache.py",
        cmds,
        "main",
        objects=["nClothShape1"],
        directory="/tmp/cache",
        start_frame=1,
        end_frame=24,
    )

    assert result["success"] is True, result
    assert result["context"]["count"] == 1


def test_skill_delete_ncache_removes_cache_nodes():
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})

    result = load_and_call(
        "maya-dynamics/scripts/delete_ncache.py",
        cmds,
        "main",
        cache_nodes=["cacheFile1"],
    )

    assert result["success"] is True, result
    assert result["context"]["deleted"] == ["cacheFile1"]


def test_skill_delete_ncache_surfaces_removed_files(tmp_path):
    """A tool that deletes files must tell the caller which ones."""
    (tmp_path / "hero.mcx").write_text("x", encoding="utf-8")
    (tmp_path / "hero.xml").write_text("x", encoding="utf-8")
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})
    cmds.getAttr = lambda plug: str(tmp_path) + "/" if plug.endswith("cachePath") else "hero"

    result = load_and_call(
        "maya-dynamics/scripts/delete_ncache.py",
        cmds,
        "main",
        cache_nodes=["cacheFile1"],
        delete_files=True,
    )

    assert result["success"] is True, result
    removed = {pathlib.Path(p).name for p in result["context"]["removed_files"]}
    assert removed == {"hero.mcx", "hero.xml"}
    assert "removed 2 cache file(s)" in result["message"]


def test_skill_delete_ncache_refuses_a_non_cachefile_node():
    cmds = _FakeCmds(existing={"pCube1": "mesh"})

    result = load_and_call(
        "maya-dynamics/scripts/delete_ncache.py",
        cmds,
        "main",
        cache_nodes=["pCube1"],
    )

    assert result["success"] is False
    assert _calls(cmds, "delete") == []


def test_skill_set_ncloth_properties_edits_shapes():
    cmds = _FakeCmds(existing={"nClothShape1": "nCloth"})

    result = load_and_call(
        "maya-dynamics/scripts/set_ncloth_properties.py",
        cmds,
        "main",
        nodes=["nClothShape1"],
        bend_resistance=0.4,
    )

    assert result["success"] is True, result
    assert _setattr(cmds)["nClothShape1.bendResistance"] == (0.4,)


def test_skill_create_rigid_constraint_uses_nail_by_default():
    cmds = _FakeCmds(existing={"rb1": "rigidBody", "rb2": "rigidBody"})

    result = load_and_call(
        "maya-dynamics/scripts/create_rigid_constraint.py",
        cmds,
        "main",
        objects=["rb1", "rb2"],
    )

    assert result["success"] is True, result
    assert _calls(cmds, "rigidConstraint")[0][2]["type"] == "nail"


def test_skill_create_nrigid_creates_collider():
    cmds = _FakeCmds(existing={"pCube1": "mesh"})

    result = load_and_call(
        "maya-dynamics/scripts/create_nrigid.py",
        cmds,
        "main",
        objects=["pCube1"],
    )

    assert result["success"] is True, result
    assert result["context"]["nrigid_nodes"] == ["nRigidShape1"]


def test_skill_create_nconstraint_returns_type():
    cmds = _FakeCmds(existing={"clothShape": "nCloth", "collider": "mesh"})

    result = load_and_call(
        "maya-dynamics/scripts/create_nconstraint.py",
        cmds,
        "main",
        objects=["clothShape"],
        target="collider",
        constraint_type="weld",
    )

    assert result["success"] is True, result
    assert result["context"]["constraint_type"] == "weld"


def test_skill_set_nucleus_properties_requires_solver():
    result = load_and_call(
        "maya-dynamics/scripts/set_nucleus_properties.py",
        _FakeCmds(),
        "main",
        gravity=9.8,
    )

    assert result["success"] is False


if __name__ == "__main__" and MAYA_CHECK_ARGV in sys.argv:
    # Child-interpreter mode: boot Maya and compare the field tables. Kept out
    # of the pytest process because maya.standalone mutates global state.
    sys.exit(_maya_check_main())
