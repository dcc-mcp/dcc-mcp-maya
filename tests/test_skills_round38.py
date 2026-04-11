"""Round 38 deep edge-case tests: maya-grooming, maya-muscle, maya-mocap + server unregister API.

Tests:
- TestCreateNHairSystem: MEL mock, missing mesh, no hair system created, custom hair_length
- TestSetNHairAttribute: missing node, wrong type (nucleus not hairSystem), happy path, prompt
- TestListHairSystems: empty, one system with stiffness, getAttr exception fallback, attributeQuery=False
- TestAddNHairCache: missing node, default frames from playback, explicit frames, mel cache call
- TestCreateMuscleCapsule: missing start_joint, missing end_joint, happy path, custom name, rename safe
- TestSetMuscleAttribute: missing node, setAttr exception, happy path, prompt
- TestListMuscles: empty, two nodes, getAttr exception → None, radius values in context
- TestApplyMuscleSkin: missing mesh, no muscles in params or scene, with muscles param, scene muscles fallback
- TestImportMocap: no file_path, file_not_found, unsupported extension, bvh happy path, fbx happy path
- TestCreateHIKDefinition: no character_name, no joint_mapping, unknown slot skipped, missing joint skipped
- TestBakeMocapToRig: no source, no target, no joints in scene, happy path with bakeResults
- TestCleanMocapKeys: no joints + no scene joints, filter existing joints, all scene joints, key count
- TestServerUnregisterSkill: method exists, delegates to registry.unregister, no-registry graceful
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest
from conftest import load_and_call, load_and_call_with_mel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_grooming(script: str, mock_cmds: MagicMock, **kwargs) -> dict:
    return load_and_call("maya-grooming/scripts/{}.py".format(script), mock_cmds, **kwargs)


def _call_grooming_mel(script: str, mock_cmds: MagicMock, mock_mel: MagicMock, **kwargs) -> dict:
    return load_and_call_with_mel(
        "maya-grooming/scripts/{}.py".format(script), mock_cmds, mock_mel, **kwargs
    )


def _call_muscle(script: str, mock_cmds: MagicMock, mock_mel: MagicMock = None, **kwargs) -> dict:
    if mock_mel is not None:
        return load_and_call_with_mel(
            "maya-muscle/scripts/{}.py".format(script), mock_cmds, mock_mel, **kwargs
        )
    return load_and_call("maya-muscle/scripts/{}.py".format(script), mock_cmds, **kwargs)


def _call_mocap(script: str, mock_cmds: MagicMock, mock_mel: MagicMock = None, **kwargs) -> dict:
    if mock_mel is not None:
        return load_and_call_with_mel(
            "maya-mocap/scripts/{}.py".format(script), mock_cmds, mock_mel, **kwargs
        )
    return load_and_call("maya-mocap/scripts/{}.py".format(script), mock_cmds, **kwargs)


def _make_cmds(**overrides) -> MagicMock:
    m = MagicMock()
    m.objExists.return_value = True
    m.ls.return_value = []
    m.playbackOptions.return_value = 1.0
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


# ---------------------------------------------------------------------------
# TestCreateNHairSystem
# ---------------------------------------------------------------------------

class TestCreateNHairSystem:
    def test_missing_mesh_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = _call_grooming("create_nhair_system", cmds, mesh="no_mesh")
        assert result["success"] is False
        assert "no_mesh" in result["message"].lower() or "not found" in result["message"].lower()

    def test_happy_path_returns_hair_system(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.side_effect = lambda **kw: (
            ["hairSystem1"] if kw.get("type") == "hairSystem"
            else ["follicle1", "follicle2"] if kw.get("type") == "follicle"
            else []
        )
        mel = MagicMock()
        result = load_and_call_with_mel(
            "maya-grooming/scripts/create_nhair_system.py", cmds, mel,
            mesh="pSphere1",
        )
        assert result["success"] is True
        assert result["context"]["hair_system"] == "hairSystem1"
        assert result["context"]["follicle_count"] == 2

    def test_no_hair_system_created_returns_empty_string(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.return_value = []
        mel = MagicMock()
        result = load_and_call_with_mel(
            "maya-grooming/scripts/create_nhair_system.py", cmds, mel,
            mesh="pSphere1",
        )
        assert result["success"] is True
        assert result["context"]["hair_system"] == ""

    def test_custom_hair_length_calls_setAttr(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.side_effect = lambda **kw: (
            ["hairSystem1"] if kw.get("type") == "hairSystem"
            else ["follicle1"] if kw.get("type") == "follicle"
            else []
        )
        mel = MagicMock()
        result = load_and_call_with_mel(
            "maya-grooming/scripts/create_nhair_system.py", cmds, mel,
            mesh="pSphere1",
            hair_length=10.0,
        )
        assert result["success"] is True
        cmds.setAttr.assert_called_once()

    def test_default_hair_length_skips_setAttr(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.side_effect = lambda **kw: (
            ["hairSystem1"] if kw.get("type") == "hairSystem"
            else []
        )
        mel = MagicMock()
        result = load_and_call_with_mel(
            "maya-grooming/scripts/create_nhair_system.py", cmds, mel,
            mesh="pSphere1",
            hair_length=5.0,
        )
        assert result["success"] is True
        cmds.setAttr.assert_not_called()

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.return_value = []
        mel = MagicMock()
        result = load_and_call_with_mel(
            "maya-grooming/scripts/create_nhair_system.py", cmds, mel,
            mesh="pSphere1",
        )
        assert result.get("prompt")

    def test_uv_density_passed_to_mel(self):
        """cmds.mel.eval should be called with the uv_density value embedded."""
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.return_value = []
        mel = MagicMock()
        cmds.mel = MagicMock()
        load_and_call_with_mel(
            "maya-grooming/scripts/create_nhair_system.py", cmds, mel,
            mesh="pSphere1",
            uv_density=5,
        )
        call_args = cmds.mel.eval.call_args_list
        assert any("5" in str(a) for a in call_args)


# ---------------------------------------------------------------------------
# TestSetNHairAttribute
# ---------------------------------------------------------------------------

class TestSetNHairAttribute:
    def test_missing_node_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = _call_grooming("set_nhair_attribute", cmds,
                                hair_system="hs1", attribute="stiffness", value=0.5)
        assert result["success"] is False

    def test_happy_path(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        result = _call_grooming("set_nhair_attribute", cmds,
                                hair_system="hairSystem1", attribute="stiffness", value=0.8)
        assert result["success"] is True
        assert result["context"]["hair_system"] == "hairSystem1"
        assert result["context"]["attribute"] == "stiffness"
        assert result["context"]["value"] == pytest.approx(0.8)

    def test_setAttr_called_correctly(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        _call_grooming("set_nhair_attribute", cmds,
                       hair_system="hairSystem1", attribute="damping", value=0.3)
        cmds.setAttr.assert_called_once_with("hairSystem1.damping", 0.3)

    def test_setAttr_exception_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.setAttr.side_effect = RuntimeError("locked attr")
        result = _call_grooming("set_nhair_attribute", cmds,
                                hair_system="hairSystem1", attribute="stiffness", value=0.5)
        assert result["success"] is False

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        result = _call_grooming("set_nhair_attribute", cmds,
                                hair_system="hs1", attribute="stiffness", value=0.5)
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestListHairSystems
# ---------------------------------------------------------------------------

class TestListHairSystems:
    def test_empty_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = _call_grooming("list_hair_systems", cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["hair_systems"] == []

    def test_single_system_with_stiffness(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["hairSystem1"] if kw.get("type") == "hairSystem" else []
        )
        cmds.listRelatives.return_value = ["hairSystem1Transform"]
        cmds.listConnections.return_value = []
        cmds.attributeQuery.return_value = True
        cmds.getAttr.return_value = 0.7

        result = _call_grooming("list_hair_systems", cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["hair_systems"][0]["stiffness"] == pytest.approx(0.7)

    def test_getAttr_exception_returns_none_stiffness(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["hairSystem1"] if kw.get("type") == "hairSystem" else []
        )
        cmds.listRelatives.return_value = []
        cmds.listConnections.return_value = []
        cmds.attributeQuery.return_value = True
        cmds.getAttr.side_effect = RuntimeError("no attr")

        result = _call_grooming("list_hair_systems", cmds)
        assert result["success"] is True
        assert result["context"]["hair_systems"][0]["stiffness"] is None

    def test_no_stiffness_attr(self):
        """When attributeQuery returns False, stiffness stays None."""
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["hairSystem1"] if kw.get("type") == "hairSystem" else []
        )
        cmds.listRelatives.return_value = []
        cmds.listConnections.return_value = []
        cmds.attributeQuery.return_value = False

        result = _call_grooming("list_hair_systems", cmds)
        assert result["context"]["hair_systems"][0]["stiffness"] is None

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = _call_grooming("list_hair_systems", cmds)
        assert result.get("prompt")

    def test_nucleus_connected(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["hairSystem1"] if kw.get("type") == "hairSystem" else []
        )
        cmds.listRelatives.return_value = []
        cmds.attributeQuery.return_value = False

        def _listConnections(node, **kw):
            if kw.get("type") == "nucleus":
                return ["nucleus1"]
            return []
        cmds.listConnections.side_effect = _listConnections

        result = _call_grooming("list_hair_systems", cmds)
        assert result["context"]["hair_systems"][0]["nucleus"] == "nucleus1"


# ---------------------------------------------------------------------------
# TestAddNHairCache
# ---------------------------------------------------------------------------

class TestAddNHairCache:
    def test_missing_node_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = _call_grooming("add_nhair_cache", cmds, hair_system="hs_missing")
        assert result["success"] is False

    def test_explicit_frames(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        result = _call_grooming("add_nhair_cache", cmds,
                                hair_system="hairSystem1",
                                start_frame=10, end_frame=50)
        assert result["success"] is True
        assert result["context"]["start_frame"] == 10
        assert result["context"]["end_frame"] == 50

    def test_default_frames_from_playback(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.playbackOptions.return_value = 24.0
        result = _call_grooming("add_nhair_cache", cmds, hair_system="hairSystem1")
        assert result["context"]["start_frame"] == 24
        assert result["context"]["end_frame"] == 24

    def test_mel_cache_called(self):
        """cmds.mel.eval should be called with the cache MEL command."""
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.playbackOptions.return_value = 1.0
        result = _call_grooming("add_nhair_cache", cmds, hair_system="hs1")
        assert result["success"] is True
        cmds.mel.eval.assert_called_once()

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.playbackOptions.return_value = 1.0
        result = _call_grooming("add_nhair_cache", cmds, hair_system="hs1")
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestCreateMuscleCapsule
# ---------------------------------------------------------------------------

class TestCreateMuscleCapsule:
    def test_missing_start_joint(self):
        cmds = _make_cmds()
        cmds.objExists.side_effect = lambda name: name != "jnt_start"
        mel = MagicMock()
        result = _call_muscle("create_muscle_capsule", cmds, mel,
                              start_joint="jnt_start", end_joint="jnt_end")
        assert result["success"] is False
        assert "jnt_start" in result["message"].lower() or "not found" in result["message"].lower()

    def test_missing_end_joint(self):
        cmds = _make_cmds()
        cmds.objExists.side_effect = lambda name: name != "jnt_end"
        mel = MagicMock()
        result = _call_muscle("create_muscle_capsule", cmds, mel,
                              start_joint="jnt_start", end_joint="jnt_end")
        assert result["success"] is False

    def test_happy_path(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.side_effect = lambda **kw: (
            ["cMuscleObject1"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.return_value = []
        mel = MagicMock()
        result = _call_muscle("create_muscle_capsule", cmds, mel,
                              start_joint="jnt_start", end_joint="jnt_end")
        assert result["success"] is True
        assert result["context"]["muscle_node"] == "cMuscleObject1"

    def test_custom_name_triggers_rename(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.side_effect = lambda **kw: (
            ["cMuscleObject1"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.return_value = ["cMuscleTransform1"]
        mel = MagicMock()
        _call_muscle("create_muscle_capsule", cmds, mel,
                     start_joint="jnt_start", end_joint="jnt_end",
                     name="my_muscle")
        cmds.rename.assert_called_once()

    def test_rename_exception_safe(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        # After rename, ls still returns the old node
        cmds.ls.side_effect = lambda **kw: (
            ["cMuscleObject1"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.return_value = ["cMuscleTransform1"]
        cmds.rename.return_value = "my_muscle"
        mel = MagicMock()
        # Should not raise even if subsequent ls fails
        result = _call_muscle("create_muscle_capsule", cmds, mel,
                              start_joint="jnt_start", end_joint="jnt_end",
                              name="my_muscle")
        assert result["success"] is True

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.side_effect = lambda **kw: (
            ["cMuscleObject1"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.return_value = []
        mel = MagicMock()
        result = _call_muscle("create_muscle_capsule", cmds, mel,
                              start_joint="jnt_start", end_joint="jnt_end")
        assert result.get("prompt")

    def test_setAttr_radius_called_twice(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.side_effect = lambda **kw: (
            ["cMuscleObject1"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.return_value = []
        mel = MagicMock()
        _call_muscle("create_muscle_capsule", cmds, mel,
                     start_joint="jnt_start", end_joint="jnt_end", radius=2.5)
        calls = [str(c) for c in cmds.setAttr.call_args_list]
        assert any("radius0" in c and "2.5" in c for c in calls)
        assert any("radius1" in c and "2.5" in c for c in calls)


# ---------------------------------------------------------------------------
# TestSetMuscleAttribute
# ---------------------------------------------------------------------------

class TestSetMuscleAttribute:
    def test_missing_node(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = _call_muscle("set_muscle_attribute", cmds,
                              muscle_node="no_node", attribute="stiffness", value=0.5)
        assert result["success"] is False

    def test_happy_path(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        result = _call_muscle("set_muscle_attribute", cmds,
                              muscle_node="cMuscleObject1", attribute="jiggle", value=0.3)
        assert result["success"] is True
        cmds.setAttr.assert_called_once_with("cMuscleObject1.jiggle", 0.3)

    def test_setAttr_exception_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.setAttr.side_effect = RuntimeError("attr locked")
        result = _call_muscle("set_muscle_attribute", cmds,
                              muscle_node="cMuscleObject1", attribute="stiffness", value=1.0)
        assert result["success"] is False

    def test_context_keys(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        result = _call_muscle("set_muscle_attribute", cmds,
                              muscle_node="cMuscleObject1", attribute="radius0", value=2.0)
        ctx = result["context"]
        assert ctx["attribute"] == "radius0"
        assert ctx["value"] == pytest.approx(2.0)

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        result = _call_muscle("set_muscle_attribute", cmds,
                              muscle_node="cMuscleObject1", attribute="stiffness", value=0.5)
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestListMuscles
# ---------------------------------------------------------------------------

class TestListMuscles:
    def test_empty_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = _call_muscle("list_muscles", cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_two_muscles(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["muscle1", "muscle2"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.side_effect = lambda node, **kw: (
            ["muscle1Transform"] if node == "muscle1" else ["muscle2Transform"]
        )
        cmds.getAttr.return_value = 1.5
        result = _call_muscle("list_muscles", cmds)
        assert result["context"]["count"] == 2
        assert result["context"]["muscles"][0]["radius0"] == pytest.approx(1.5)

    def test_getAttr_exception_returns_none(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["muscle1"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.return_value = []
        cmds.getAttr.side_effect = RuntimeError("not found")
        result = _call_muscle("list_muscles", cmds)
        assert result["context"]["muscles"][0]["radius0"] is None
        assert result["context"]["muscles"][0]["radius1"] is None

    def test_no_parent_empty_string(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["muscle1"] if kw.get("type") == "cMuscleObject" else []
        )
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = 1.0
        result = _call_muscle("list_muscles", cmds)
        assert result["context"]["muscles"][0]["transform"] == ""

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = _call_muscle("list_muscles", cmds)
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestApplyMuscleSkin
# ---------------------------------------------------------------------------

class TestApplyMuscleSkin:
    def test_missing_mesh_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        mel = MagicMock()
        result = _call_muscle("apply_muscle_skin", cmds, mel, mesh="no_mesh")
        assert result["success"] is False

    def test_no_muscles_in_params_or_scene(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.ls.return_value = []
        mel = MagicMock()
        result = _call_muscle("apply_muscle_skin", cmds, mel, mesh="pSphere1")
        assert result["success"] is False
        assert "muscle" in result["message"].lower()

    def test_muscles_from_params(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = ["muscleTransform1"]
        cmds.ls.side_effect = lambda **kw: (
            ["cMuscleSystem1"] if kw.get("type") == "cMuscleSystem" else []
        )
        mel = MagicMock()
        result = _call_muscle("apply_muscle_skin", cmds, mel,
                              mesh="pSphere1", muscles=["cMuscleObject1"])
        assert result["success"] is True
        assert result["context"]["muscles_connected"] == 1
        assert result["context"]["system_node"] == "cMuscleSystem1"

    def test_muscles_from_scene_fallback(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = []
        def _ls(**kw):
            if kw.get("type") == "cMuscleObject":
                return ["muscle1", "muscle2"]
            if kw.get("type") == "cMuscleSystem":
                return ["cMuscleSystem1"]
            return []
        cmds.ls.side_effect = _ls
        mel = MagicMock()
        result = _call_muscle("apply_muscle_skin", cmds, mel, mesh="pSphere1")
        assert result["success"] is True
        assert result["context"]["muscles_connected"] == 2

    def test_mel_eval_called(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = []
        cmds.ls.side_effect = lambda **kw: (
            ["muscle1"] if kw.get("type") == "cMuscleObject"
            else ["cMuscleSystem1"] if kw.get("type") == "cMuscleSystem"
            else []
        )
        mel = MagicMock()
        _call_muscle("apply_muscle_skin", cmds, mel, mesh="pSphere1")
        mel.eval.assert_called_once()

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.listRelatives.return_value = []
        cmds.ls.side_effect = lambda **kw: (
            ["muscle1"] if kw.get("type") == "cMuscleObject"
            else ["cMuscleSystem1"] if kw.get("type") == "cMuscleSystem"
            else []
        )
        mel = MagicMock()
        result = _call_muscle("apply_muscle_skin", cmds, mel, mesh="pSphere1")
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestImportMocap
# ---------------------------------------------------------------------------

class TestImportMocap:
    def test_no_file_path(self):
        cmds = _make_cmds()
        result = _call_mocap("import_mocap", cmds, file_path="")
        assert result["success"] is False
        assert "file_path" in result["message"].lower() or "missing" in result["message"].lower()

    def test_file_not_found(self):
        cmds = _make_cmds()
        result = _call_mocap("import_mocap", cmds,
                             file_path="C:/nonexistent/file.bvh")
        assert result["success"] is False
        assert "not found" in result["message"].lower() or "file" in result["message"].lower()

    def test_unsupported_extension(self, tmp_path):
        p = tmp_path / "motion.abc"
        p.write_bytes(b"fake")
        cmds = _make_cmds()
        result = _call_mocap("import_mocap", cmds, file_path=str(p))
        assert result["success"] is False
        assert "unsupported" in result["message"].lower() or ".abc" in result["message"].lower()

    def test_bvh_happy_path(self, tmp_path):
        p = tmp_path / "motion.bvh"
        p.write_bytes(b"BVH data")
        cmds = _make_cmds()
        # First call (before import) returns empty, second call (after import) returns 2 joints
        call_count = [0]
        def _ls(**kw):
            if kw.get("type") == "joint":
                call_count[0] += 1
                return [] if call_count[0] == 1 else ["mocap:joint1", "mocap:joint2"]
            return []
        cmds.ls.side_effect = _ls
        cmds.listRelatives.return_value = []
        result = _call_mocap("import_mocap", cmds, file_path=str(p))
        assert result["success"] is True
        assert result["context"]["joint_count"] == 2
        cmds.file.assert_called_once()

    def test_fbx_happy_path(self, tmp_path):
        p = tmp_path / "motion.fbx"
        p.write_bytes(b"FBX data")
        cmds = _make_cmds()
        # Before import: empty, after: 3 joints
        call_count = [0]
        def _ls(**kw):
            if kw.get("type") == "joint":
                call_count[0] += 1
                return ["j1", "j2", "j3"] if call_count[0] > 1 else []
            return []
        cmds.ls.side_effect = _ls
        cmds.listRelatives.return_value = []
        result = _call_mocap("import_mocap", cmds, file_path=str(p))
        assert result["success"] is True
        assert result["context"]["joint_count"] == 3

    def test_prompt_present(self, tmp_path):
        p = tmp_path / "motion.bvh"
        p.write_bytes(b"x")
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = _call_mocap("import_mocap", cmds, file_path=str(p))
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestCreateHIKDefinition
# ---------------------------------------------------------------------------

class TestCreateHIKDefinition:
    def _call(self, mock_cmds, mock_mel, **kwargs):
        return load_and_call_with_mel(
            "maya-mocap/scripts/create_hik_definition.py",
            mock_cmds,
            mock_mel,
            **kwargs,
        )

    def test_no_character_name(self):
        cmds = _make_cmds()
        mel = MagicMock()
        result = self._call(cmds, mel, character_name="", joint_mapping={"Hips": "hip_jnt"})
        assert result["success"] is False
        assert "character_name" in result["message"].lower() or "missing" in result["message"].lower()

    def test_no_joint_mapping(self):
        cmds = _make_cmds()
        mel = MagicMock()
        result = self._call(cmds, mel, character_name="char1", joint_mapping={})
        assert result["success"] is False

    def test_unknown_slot_skipped(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        mel = MagicMock()
        mel.eval.side_effect = lambda s: "char_node" if "hikCreateCharacter" in s else None
        result = self._call(cmds, mel, character_name="char1",
                            joint_mapping={"UnknownSlot": "some_joint"})
        assert result["success"] is True
        assert result["context"]["mapped_count"] == 0
        assert len(result["context"]["skipped"]) == 1
        assert result["context"]["skipped"][0]["reason"] == "Unknown HIK slot"

    def test_missing_joint_skipped(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        mel = MagicMock()
        mel.eval.side_effect = lambda s: "char_node" if "hikCreateCharacter" in s else None
        result = self._call(cmds, mel, character_name="char1",
                            joint_mapping={"Hips": "missing_hips"})
        assert result["success"] is True
        assert result["context"]["mapped_count"] == 0
        assert any(s.get("reason") == "Joint not found" for s in result["context"]["skipped"])

    def test_happy_path_maps_joints(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        mel = MagicMock()
        mel.eval.side_effect = lambda s: "char_node" if "hikCreateCharacter" in s else None
        result = self._call(cmds, mel, character_name="char1",
                            joint_mapping={"Hips": "hip_jnt", "Spine": "spine_jnt"})
        assert result["success"] is True
        assert result["context"]["mapped_count"] == 2
        assert len(result["context"]["mapped"]) == 2

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        mel = MagicMock()
        mel.eval.side_effect = lambda s: "char_node" if "hikCreateCharacter" in s else None
        result = self._call(cmds, mel, character_name="char1",
                            joint_mapping={"Hips": "hip_jnt"})
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestBakeMocapToRig
# ---------------------------------------------------------------------------

class TestBakeMocapToRig:
    def _call(self, mock_cmds, mock_mel, **kwargs):
        return load_and_call_with_mel(
            "maya-mocap/scripts/bake_mocap_to_rig.py",
            mock_cmds,
            mock_mel,
            **kwargs,
        )

    def test_missing_source_character(self):
        cmds = _make_cmds()
        mel = MagicMock()
        result = self._call(cmds, mel, source_character="", target_character="rig")
        assert result["success"] is False

    def test_missing_target_character(self):
        cmds = _make_cmds()
        mel = MagicMock()
        result = self._call(cmds, mel, source_character="src", target_character="")
        assert result["success"] is False

    def test_no_joints_in_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.playbackOptions.return_value = 1.0
        mel = MagicMock()
        result = self._call(cmds, mel, source_character="src", target_character="rig")
        assert result["success"] is False
        assert "joint" in result["message"].lower() or "no joint" in result["message"].lower()

    def test_happy_path(self):
        cmds = _make_cmds()
        cmds.playbackOptions.return_value = 1.0
        cmds.ls.side_effect = lambda **kw: (
            ["joint1", "joint2", "joint3"] if kw.get("type") == "joint" else []
        )
        mel = MagicMock()
        result = self._call(cmds, mel, source_character="src", target_character="rig")
        assert result["success"] is True
        assert result["context"]["baked_joints"] == 3
        cmds.bakeResults.assert_called_once()

    def test_explicit_frame_range(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["joint1"] if kw.get("type") == "joint" else []
        )
        mel = MagicMock()
        result = self._call(cmds, mel, source_character="src", target_character="rig",
                            start_frame=5, end_frame=25)
        assert result["context"]["start_frame"] == 5
        assert result["context"]["end_frame"] == 25

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["joint1"] if kw.get("type") == "joint" else []
        )
        cmds.playbackOptions.return_value = 1.0
        mel = MagicMock()
        result = self._call(cmds, mel, source_character="src", target_character="rig")
        assert result.get("prompt")


# ---------------------------------------------------------------------------
# TestCleanMocapKeys
# ---------------------------------------------------------------------------

class TestCleanMocapKeys:
    def test_no_joints_and_empty_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = _call_mocap("clean_mocap_keys", cmds)
        assert result["success"] is False
        assert "joint" in result["message"].lower() or "no joint" in result["message"].lower()

    def test_filter_existing_joints(self):
        cmds = _make_cmds()
        cmds.objExists.side_effect = lambda n: n == "joint1"
        cmds.keyframe.return_value = 50
        result = _call_mocap("clean_mocap_keys", cmds,
                             joints=["joint1", "missing_joint"])
        # Only existing joint used; success should be True
        assert result["success"] is True
        assert result["context"]["joints_processed"] == 1

    def test_all_scene_joints_if_none_specified(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["jnt1", "jnt2"] if kw.get("type") == "joint" else []
        )
        cmds.keyframe.return_value = 100
        result = _call_mocap("clean_mocap_keys", cmds)
        assert result["success"] is True
        assert result["context"]["joints_processed"] == 2

    def test_key_count_in_context(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["jnt1"] if kw.get("type") == "joint" else []
        )
        call_idx = [0]
        def _keyframe(*a, **kw):
            call_idx[0] += 1
            return 80 if call_idx[0] == 1 else 40
        cmds.keyframe.side_effect = _keyframe
        result = _call_mocap("clean_mocap_keys", cmds)
        assert result["context"]["keys_before"] == 80
        assert result["context"]["keys_after"] == 40
        assert result["context"]["keys_removed"] == 40

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = lambda **kw: (
            ["jnt1"] if kw.get("type") == "joint" else []
        )
        cmds.keyframe.return_value = 10
        result = _call_mocap("clean_mocap_keys", cmds)
        assert result.get("prompt")

    def test_all_joints_missing_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = _call_mocap("clean_mocap_keys", cmds,
                             joints=["jnt_a", "jnt_b"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestServerUnregisterSkill
# ---------------------------------------------------------------------------

class TestServerUnregisterSkill:
    """Verify MayaMcpServer.unregister_skill delegates to registry.unregister (v0.12.6+)."""

    def _make_server(self):
        """Return a MayaMcpServer with all dcc_mcp_core imports mocked."""
        import importlib

        mock_core = MagicMock()
        mock_skill_manager = MagicMock()
        mock_registry = MagicMock()
        mock_skill_manager._registry = mock_registry
        mock_core.create_skill_manager.return_value = mock_skill_manager
        mock_core.McpHttpConfig.return_value = MagicMock()

        with patch.dict(sys.modules, {
            "dcc_mcp_core": mock_core,
            "maya": MagicMock(),
            "maya.cmds": MagicMock(),
        }):
            srv_mod2 = importlib.import_module("dcc_mcp_maya.server")
            return srv_mod2.MayaMcpServer.__new__(srv_mod2.MayaMcpServer), mock_registry, mock_skill_manager

    def test_server_has_unregister_skill_method(self):
        """MayaMcpServer must expose an unregister_skill method."""
        mock_core = MagicMock()
        mock_skill_manager = MagicMock()
        mock_registry = MagicMock()
        mock_skill_manager._registry = mock_registry
        mock_core.create_skill_manager.return_value = mock_skill_manager
        mock_core.McpHttpConfig.return_value = MagicMock()

        with patch.dict(sys.modules, {
            "dcc_mcp_core": mock_core,
            "maya": MagicMock(),
            "maya.cmds": MagicMock(),
        }):
            import importlib
            srv_mod = importlib.import_module("dcc_mcp_maya.server")
            importlib.reload(srv_mod)
            assert hasattr(srv_mod.MayaMcpServer, "unregister_skill")

    def test_unregister_delegates_to_registry(self):
        mock_core = MagicMock()
        mock_skill_manager = MagicMock()
        mock_registry = MagicMock()
        mock_skill_manager._registry = mock_registry
        mock_core.create_skill_manager.return_value = mock_skill_manager
        mock_core.McpHttpConfig.return_value = MagicMock()

        with patch.dict(sys.modules, {
            "dcc_mcp_core": mock_core,
            "maya": MagicMock(),
            "maya.cmds": MagicMock(),
        }):
            import importlib
            srv_mod = importlib.import_module("dcc_mcp_maya.server")
            importlib.reload(srv_mod)
            srv = srv_mod.MayaMcpServer(port=0)
            srv.unregister_skill("maya_scene__create_object")
            mock_registry.unregister.assert_called_once_with("maya_scene__create_object", dcc_name=None)

    def test_unregister_no_registry_graceful(self):
        """When registry is None, unregister_skill should not raise."""
        mock_core = MagicMock()
        mock_skill_manager = MagicMock()
        mock_skill_manager._registry = None  # No registry
        mock_core.create_skill_manager.return_value = mock_skill_manager
        mock_core.McpHttpConfig.return_value = MagicMock()

        with patch.dict(sys.modules, {
            "dcc_mcp_core": mock_core,
            "maya": MagicMock(),
            "maya.cmds": MagicMock(),
        }):
            import importlib
            srv_mod = importlib.import_module("dcc_mcp_maya.server")
            importlib.reload(srv_mod)
            srv = srv_mod.MayaMcpServer(port=0)
            # Should not raise
            srv.unregister_skill("maya_scene__create_object")

    def test_unregister_with_dcc_name(self):
        mock_core = MagicMock()
        mock_skill_manager = MagicMock()
        mock_registry = MagicMock()
        mock_skill_manager._registry = mock_registry
        mock_core.create_skill_manager.return_value = mock_skill_manager
        mock_core.McpHttpConfig.return_value = MagicMock()

        with patch.dict(sys.modules, {
            "dcc_mcp_core": mock_core,
            "maya": MagicMock(),
            "maya.cmds": MagicMock(),
        }):
            import importlib
            srv_mod = importlib.import_module("dcc_mcp_maya.server")
            importlib.reload(srv_mod)
            srv = srv_mod.MayaMcpServer(port=0)
            srv.unregister_skill("maya_scene__create_object", dcc_name="maya")
            mock_registry.unregister.assert_called_once_with(
                "maya_scene__create_object", dcc_name="maya"
            )

    def test_unregister_exception_graceful(self):
        """Registry.unregister raising should be caught and return gracefully."""
        mock_core = MagicMock()
        mock_skill_manager = MagicMock()
        mock_registry = MagicMock()
        mock_registry.unregister.side_effect = KeyError("not found")
        mock_skill_manager._registry = mock_registry
        mock_core.create_skill_manager.return_value = mock_skill_manager
        mock_core.McpHttpConfig.return_value = MagicMock()

        with patch.dict(sys.modules, {
            "dcc_mcp_core": mock_core,
            "maya": MagicMock(),
            "maya.cmds": MagicMock(),
        }):
            import importlib
            srv_mod = importlib.import_module("dcc_mcp_maya.server")
            importlib.reload(srv_mod)
            srv = srv_mod.MayaMcpServer(port=0)
            # Should not raise
            srv.unregister_skill("nonexistent_skill")
