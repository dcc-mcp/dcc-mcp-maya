"""Unit tests for the Nucleus contract module (``dcc_mcp_maya.nucleus``).

These cover the typed boundary that the ``maya-dynamics`` nCloth / nRigid /
nConstraint / field / nCache tools are built on.  A fake ``cmds`` object keeps
the tests importable without a Maya interpreter.
"""

from __future__ import annotations

import pathlib
from contextlib import contextmanager

import pytest
from conftest import load_and_call

from dcc_mcp_maya import nucleus as nucleus_mod
from dcc_mcp_maya.nucleus import (
    CACHEABLE_NODE_TYPES,
    FIELD_COMMANDS,
    NCONSTRAINT_TYPES,
    NUCLEUS_ATTRS,
    NucleusContractError,
    _cache_file_paths,
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
    """Real-filesystem check: both Maya cache layouts are removed."""
    for name in ("hero.mcx", "hero.xml", "heroFrame1.mcx", "heroFrame2.mcx", "unrelated.mcx"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    cmds = _FakeCmds(existing={"cacheFile1": "cacheFile"})
    cmds.getAttr = lambda plug: str(tmp_path) + "/" if plug.endswith("cachePath") else "hero"

    result = delete_cache(cmds, cache_nodes=["cacheFile1"], delete_files=True)

    assert result["delete_files"] is True
    removed = {pathlib.Path(p).name for p in result["removed_files"]}
    assert removed == {"hero.mcx", "hero.xml", "heroFrame1.mcx", "heroFrame2.mcx"}
    assert (tmp_path / "unrelated.mcx").exists()


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
