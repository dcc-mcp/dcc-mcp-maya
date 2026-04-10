"""Round 19: tests for maya-mocap, maya-cloth-sim, maya-pose-library skills."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Dynamically load a skill script module bypassing hyphenated dir names."""
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{0}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "{0}_{1}".format(skill_dir.replace("-", "_"), script_name),
        script_path,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_maya():
    """Return a fresh mock_cmds and wire maya/maya.cmds/maya.utils into sys.modules."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.utils"] = MagicMock()
    sys.modules["maya.api"] = MagicMock()
    return mock_cmds


def _cleanup_maya():
    for mod in ("maya", "maya.cmds", "maya.utils", "maya.api"):
        sys.modules.pop(mod, None)


# ===========================================================================
# maya-mocap
# ===========================================================================


class TestCreateHikCharacter:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-mocap", "create_hik_character")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.pluginInfo.return_value = True
        self.mock_cmds.createNode.return_value = "Character1_hikNode"
        result = self.mod.run({"name": "Character1"})
        assert result.success is True
        assert "Character1" in result.message
        assert result.context["character_name"] == "Character1"

    def test_with_namespace(self):
        self.mock_cmds.pluginInfo.return_value = True
        self.mock_cmds.createNode.return_value = "ns:Character1_hikNode"
        result = self.mod.run({"name": "Character1", "namespace": "ns"})
        assert result.success is True
        assert result.context["character_name"] == "ns:Character1"

    def test_empty_name_error(self):
        result = self.mod.run({"name": ""})
        assert result.success is False
        assert "empty" in result.error.lower()

    def test_plugin_not_loaded_gets_loaded(self):
        self.mock_cmds.pluginInfo.return_value = False
        self.mock_cmds.createNode.return_value = "Char_hikNode"
        result = self.mod.run({"name": "Char"})
        self.mock_cmds.loadPlugin.assert_called_once_with("mayaHIK")
        assert result.success is True

    def test_exception_handling(self):
        self.mock_cmds.pluginInfo.return_value = True
        self.mock_cmds.createNode.side_effect = RuntimeError("node creation failed")
        result = self.mod.run({"name": "BadChar"})
        assert result.success is False
        assert "node creation failed" in result.error

    def test_default_name(self):
        self.mock_cmds.pluginInfo.return_value = True
        self.mock_cmds.createNode.return_value = "Character1_hikNode"
        result = self.mod.run({})
        assert result.success is True
        assert result.context["character_name"] == "Character1"


class TestDefineHikJoint:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-mocap", "define_hik_joint")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        result = self.mod.run({
            "character_node": "Char_hikNode",
            "joint": "Hip_jnt",
            "bone_name": "Hips",
        })
        assert result.success is True
        assert result.context["bone_name"] == "Hips"
        assert result.context["bone_id"] == 1

    def test_unknown_bone_name(self):
        result = self.mod.run({
            "character_node": "Char_hikNode",
            "joint": "Hip_jnt",
            "bone_name": "UnknownBone",
        })
        assert result.success is False
        assert "Unknown bone name" in result.message

    def test_empty_character_node(self):
        result = self.mod.run({"character_node": "", "joint": "j", "bone_name": "Hips"})
        assert result.success is False

    def test_empty_joint(self):
        result = self.mod.run({"character_node": "cn", "joint": "", "bone_name": "Hips"})
        assert result.success is False

    def test_setattr_called(self):
        result = self.mod.run({
            "character_node": "Char_hikNode",
            "joint": "LeftArm_jnt",
            "bone_name": "LeftArm",
        })
        assert result.success is True
        self.mock_cmds.setAttr.assert_called_once()

    def test_exception_handling(self):
        self.mock_cmds.setAttr.side_effect = RuntimeError("attr error")
        result = self.mod.run({
            "character_node": "Char_hikNode",
            "joint": "Hip_jnt",
            "bone_name": "Hips",
        })
        assert result.success is False

    def test_valid_bone_ids(self):
        """Head bone should have id=15."""
        result = self.mod.run({
            "character_node": "Char_hikNode",
            "joint": "Head_jnt",
            "bone_name": "Head",
        })
        assert result.success is True
        assert result.context["bone_id"] == 15


class TestListHikCharacters:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-mocap", "list_hik_characters")

    def teardown_method(self):
        _cleanup_maya()

    def test_empty_scene(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_two_characters(self):
        self.mock_cmds.ls.return_value = ["Char1_hikNode", "Char2_hikNode"]
        self.mock_cmds.getAttr.return_value = False
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_locked_character_reported(self):
        self.mock_cmds.ls.return_value = ["Char_hikNode"]
        self.mock_cmds.getAttr.return_value = True
        result = self.mod.run({})
        assert result.context["characters"][0]["locked"] is True

    def test_exception_handling(self):
        self.mock_cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


class TestRetargetMocap:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-mocap", "retarget_mocap")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success_no_bake(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "HIKCharacterNode"
        self.mock_cmds.createNode.return_value = "Target_retargeter"
        result = self.mod.run({
            "source_character": "SrcChar",
            "target_character": "TgtChar",
            "bake": False,
        })
        assert result.success is True
        assert result.context["baked"] is False

    def test_basic_success_with_bake(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "HIKCharacterNode"
        self.mock_cmds.createNode.return_value = "Target_retargeter"
        self.mock_cmds.playbackOptions.side_effect = [1.0, 24.0]
        result = self.mod.run({
            "source_character": "SrcChar",
            "target_character": "TgtChar",
            "bake": True,
        })
        assert result.success is True
        assert result.context["baked"] is True
        self.mock_cmds.bakeResults.assert_called_once()

    def test_empty_source_error(self):
        result = self.mod.run({"source_character": "", "target_character": "TgtChar"})
        assert result.success is False

    def test_empty_target_error(self):
        result = self.mod.run({"source_character": "SrcChar", "target_character": ""})
        assert result.success is False

    def test_node_not_found_error(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({
            "source_character": "NonExistent",
            "target_character": "TgtChar",
            "bake": False,
        })
        assert result.success is False
        assert "not found" in result.message.lower() or "not found" in result.error.lower()

    def test_wrong_node_type_error(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "transform"
        result = self.mod.run({
            "source_character": "SomeMesh",
            "target_character": "TgtChar",
            "bake": False,
        })
        assert result.success is False
        assert "HIKCharacterNode" in result.error or "Invalid" in result.message


class TestDeleteHikCharacter:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-mocap", "delete_hik_character")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "HIKCharacterNode"
        self.mock_cmds.listConnections.return_value = []
        result = self.mod.run({"character_node": "Char_hikNode"})
        assert result.success is True
        self.mock_cmds.delete.assert_called()

    def test_with_retargeters_deleted(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "HIKCharacterNode"
        self.mock_cmds.listConnections.return_value = ["Char_retargeter"]
        result = self.mod.run({"character_node": "Char_hikNode", "delete_retargeters": True})
        assert result.success is True
        assert "Char_retargeter" in result.context["deleted_nodes"]

    def test_empty_name_error(self):
        result = self.mod.run({"character_node": ""})
        assert result.success is False

    def test_node_not_found_error(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"character_node": "Missing"})
        assert result.success is False

    def test_wrong_node_type(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "transform"
        result = self.mod.run({"character_node": "SomeNode"})
        assert result.success is False

    def test_exception_handling(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "HIKCharacterNode"
        self.mock_cmds.listConnections.return_value = []
        self.mock_cmds.delete.side_effect = RuntimeError("delete failed")
        result = self.mod.run({"character_node": "Char_hikNode"})
        assert result.success is False


# ===========================================================================
# maya-cloth-sim
# ===========================================================================


class TestCreateClothObject:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-cloth-sim", "create_cloth_object")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nCloth.return_value = ["pSphere1_nCloth"]
        self.mock_cmds.attributeQuery.return_value = True
        result = self.mod.run({"mesh": "pSphere1"})
        assert result.success is True
        assert result.context["cloth_node"] == "pSphere1_nCloth"

    def test_preset_denim(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nCloth.return_value = ["cloth1"]
        self.mock_cmds.attributeQuery.return_value = True
        result = self.mod.run({"mesh": "pSphere1", "preset": "denim"})
        assert result.success is True
        assert result.context["preset"] == "denim"

    def test_empty_mesh_error(self):
        result = self.mod.run({"mesh": ""})
        assert result.success is False

    def test_mesh_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"mesh": "ghost"})
        assert result.success is False
        assert "not found" in result.message.lower() or "not found" in result.error.lower()

    def test_override_thickness(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nCloth.return_value = ["cloth1"]
        self.mock_cmds.attributeQuery.return_value = True
        result = self.mod.run({"mesh": "pSphere1", "thickness": 0.05})
        assert result.success is True

    def test_exception_handling(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nCloth.side_effect = RuntimeError("nCloth failed")
        result = self.mod.run({"mesh": "pSphere1"})
        assert result.success is False


class TestAddClothCollider:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-cloth-sim", "add_cloth_collider")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nRigid.return_value = ["pCube1_nRigid"]
        result = self.mod.run({"mesh": "pCube1"})
        assert result.success is True
        assert result.context["rigid_node"] == "pCube1_nRigid"

    def test_empty_mesh_error(self):
        result = self.mod.run({"mesh": ""})
        assert result.success is False

    def test_mesh_not_found(self):
        self.mock_cmds.objExists.return_value = False
        result = self.mod.run({"mesh": "ghost"})
        assert result.success is False

    def test_friction_clamped(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nRigid.return_value = ["rigid1"]
        result = self.mod.run({"mesh": "pCube1", "friction": 5.0})
        assert result.success is True
        # setAttr should be called with clamped value (1.0)
        calls = [c for c in self.mock_cmds.setAttr.call_args_list if "friction" in str(c)]
        assert any("1.0" in str(c) or c[0][1] == 1.0 for c in calls)

    def test_exception_handling(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nRigid.side_effect = RuntimeError("nRigid error")
        result = self.mod.run({"mesh": "pCube1"})
        assert result.success is False


class TestSimulateCloth:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-cloth-sim", "simulate_cloth")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.playbackOptions.side_effect = [1.0, 5.0]
        self.mock_cmds.ls.return_value = ["cloth1"]
        result = self.mod.run({"start_frame": 1, "end_frame": 5, "cache": False})
        assert result.success is True
        assert result.context["cloth_nodes"] == ["cloth1"]

    def test_default_time_range(self):
        self.mock_cmds.playbackOptions.side_effect = [1.0, 3.0]
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["start_frame"] == 1.0

    def test_with_cache(self):
        self.mock_cmds.playbackOptions.side_effect = [1.0, 2.0]
        self.mock_cmds.ls.return_value = ["cloth1"]
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({"cache": True, "cache_dir": tmpdir, "start_frame": 1, "end_frame": 2})
        assert result.success is True
        self.mock_cmds.cacheFile.assert_called()

    def test_no_cloth_nodes(self):
        self.mock_cmds.playbackOptions.side_effect = [1.0, 2.0]
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({"start_frame": 1, "end_frame": 2})
        assert result.success is True
        assert result.context["count"] == 0 or "0 nCloth" in result.message

    def test_exception_handling(self):
        self.mock_cmds.playbackOptions.side_effect = RuntimeError("playback error")
        result = self.mod.run({})
        assert result.success is False


class TestSetClothAttribute:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-cloth-sim", "set_cloth_attribute")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "nCloth"
        result = self.mod.run({"cloth_node": "cloth1", "attribute": "thickness", "value": 0.02})
        assert result.success is True

    def test_string_value(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "nCloth"
        result = self.mod.run({"cloth_node": "cloth1", "attribute": "note", "value": "test"})
        assert result.success is True
        self.mock_cmds.setAttr.assert_called_once()

    def test_list_value(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "nCloth"
        result = self.mod.run({"cloth_node": "cloth1", "attribute": "inputMeshAttract", "value": [1.0, 0.5]})
        assert result.success is True

    def test_empty_cloth_node_error(self):
        result = self.mod.run({"cloth_node": "", "attribute": "thickness", "value": 0.01})
        assert result.success is False

    def test_wrong_node_type(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "transform"
        result = self.mod.run({"cloth_node": "mesh1", "attribute": "thickness", "value": 0.01})
        assert result.success is False

    def test_exception_handling(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "nCloth"
        self.mock_cmds.setAttr.side_effect = RuntimeError("set failed")
        result = self.mod.run({"cloth_node": "cloth1", "attribute": "thickness", "value": 0.01})
        assert result.success is False


class TestListClothNodes:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-cloth-sim", "list_cloth_nodes")

    def teardown_method(self):
        _cleanup_maya()

    def test_empty_scene(self):
        self.mock_cmds.ls.return_value = []
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_two_cloth_nodes(self):
        self.mock_cmds.ls.return_value = ["cloth1", "cloth2"]
        self.mock_cmds.attributeQuery.return_value = True
        self.mock_cmds.getAttr.return_value = 0.01
        result = self.mod.run({})
        assert result.success is True
        assert result.context["count"] == 2

    def test_attrs_reported(self):
        self.mock_cmds.ls.return_value = ["cloth1"]
        self.mock_cmds.attributeQuery.return_value = True
        self.mock_cmds.getAttr.return_value = 1.0
        result = self.mod.run({})
        assert "thickness" in result.context["cloth_nodes"][0]

    def test_exception_handling(self):
        self.mock_cmds.ls.side_effect = RuntimeError("ls failed")
        result = self.mod.run({})
        assert result.success is False


# ===========================================================================
# maya-pose-library  (no Maya cmds needed — pure Python file I/O)
# ===========================================================================


class TestSavePose:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-pose-library", "save_pose")

    def teardown_method(self):
        _cleanup_maya()

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.attributeQuery.return_value = True
        self.mock_cmds.getAttr.return_value = 0.0
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({
                "pose_name": "test_pose",
                "objects": ["Hip_jnt"],
                "pose_dir": tmpdir,
            })
        assert result.success is True
        assert result.context["object_count"] == 1

    def test_empty_pose_name_error(self):
        result = self.mod.run({"pose_name": "", "objects": ["Hip_jnt"]})
        assert result.success is False

    def test_no_objects_no_selection_error(self):
        self.mock_cmds.ls.return_value = []
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({"pose_name": "p", "pose_dir": tmpdir})
        assert result.success is False
        assert "No objects" in result.message

    def test_file_created(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.attributeQuery.return_value = True
        self.mock_cmds.getAttr.return_value = 1.0
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({
                "pose_name": "standing",
                "objects": ["root_ctrl"],
                "pose_dir": tmpdir,
            })
            assert os.path.isfile(os.path.join(tmpdir, "standing.pose.json"))
        assert result.success is True

    def test_skips_nonexistent_objects(self):
        self.mock_cmds.objExists.return_value = False
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({
                "pose_name": "empty_pose",
                "objects": ["ghost"],
                "pose_dir": tmpdir,
            })
        # No objects written — success with count 0
        assert result.success is True
        assert result.context["object_count"] == 0

    def test_selection_used_when_no_objects(self):
        self.mock_cmds.ls.return_value = ["root_ctrl"]
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.attributeQuery.return_value = True
        self.mock_cmds.getAttr.return_value = 0.0
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({"pose_name": "sel_pose", "pose_dir": tmpdir})
        assert result.success is True


class TestApplyPose:
    def setup_method(self):
        self.mock_cmds = _mock_maya()
        self.mod = _load_script("maya-pose-library", "apply_pose")

    def teardown_method(self):
        _cleanup_maya()

    def _make_pose_file(self, tmpdir, pose_name, obj_name="root_ctrl"):
        data = {
            "name": pose_name,
            "objects": {obj_name: {"translateX": 1.0, "translateY": 2.0}},
        }
        fpath = os.path.join(tmpdir, "{0}.pose.json".format(pose_name))
        with open(fpath, "w") as fh:
            json.dump(data, fh)
        return fpath

    def test_basic_success(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.attributeQuery.return_value = True
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_pose_file(tmpdir, "standing")
            result = self.mod.run({"pose_name": "standing", "pose_dir": tmpdir})
        assert result.success is True
        assert result.context["applied_count"] == 1

    def test_pose_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({"pose_name": "nonexistent", "pose_dir": tmpdir})
        assert result.success is False
        assert "not found" in result.message.lower() or "not found" in result.error.lower()

    def test_empty_pose_name_error(self):
        result = self.mod.run({"pose_name": ""})
        assert result.success is False

    def test_blend_partial(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.attributeQuery.return_value = True
        self.mock_cmds.getAttr.return_value = 0.0
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_pose_file(tmpdir, "blend_test")
            result = self.mod.run({"pose_name": "blend_test", "pose_dir": tmpdir, "blend": 0.5})
        assert result.success is True
        assert result.context["blend"] == 0.5

    def test_namespace_prepended(self):
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.attributeQuery.return_value = True
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_pose_file(tmpdir, "ns_test")
            result = self.mod.run({"pose_name": "ns_test", "pose_dir": tmpdir, "namespace": "myNS"})
        # objExists should have been called with "myNS:root_ctrl"
        calls_str = str(self.mock_cmds.objExists.call_args_list)
        assert "myNS:root_ctrl" in calls_str
        assert result.success is True

    def test_skips_missing_objects(self):
        self.mock_cmds.objExists.return_value = False
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_pose_file(tmpdir, "ghost_pose")
            result = self.mod.run({"pose_name": "ghost_pose", "pose_dir": tmpdir})
        assert result.success is True
        assert result.context["applied_count"] == 0


class TestListPoses:
    def setup_method(self):
        self.mod = _load_script("maya-pose-library", "list_poses")

    def test_empty_directory_not_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = os.path.join(tmpdir, "poses")
            result = self.mod.run({"pose_dir": nonexistent})
        assert result.success is True
        assert result.context["count"] == 0

    def test_lists_pose_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("standing", "crouch", "run"):
                fpath = os.path.join(tmpdir, "{0}.pose.json".format(name))
                with open(fpath, "w") as fh:
                    json.dump({"name": name, "objects": {"ctrl": {"tx": 0.0}}}, fh)
            result = self.mod.run({"pose_dir": tmpdir})
        assert result.success is True
        assert result.context["count"] == 3

    def test_pose_metadata_included(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "idle.pose.json")
            with open(fpath, "w") as fh:
                json.dump({"name": "idle", "objects": {"c": {}, "d": {}}}, fh)
            result = self.mod.run({"pose_dir": tmpdir})
        assert result.context["poses"][0]["object_count"] == 2

    def test_exception_handling(self):
        result = self.mod.run({"pose_dir": "/nonexistent/path/that/also/does/not/exist"})
        # Either returns empty list (dir not exist → success) or error — both acceptable
        # but no crash
        assert hasattr(result, "success")


class TestMirrorPose:
    def setup_method(self):
        self.mod = _load_script("maya-pose-library", "mirror_pose")

    def _make_pose(self, tmpdir, name, obj_data):
        fpath = os.path.join(tmpdir, "{0}.pose.json".format(name))
        with open(fpath, "w") as fh:
            json.dump({"name": name, "objects": obj_data}, fh)
        return fpath

    def test_yz_mirror_negates_translateX(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_pose(tmpdir, "src", {"L_arm": {"translateX": 3.0, "translateY": 1.0}})
            result = self.mod.run({
                "pose_name": "src",
                "mirrored_pose_name": "mirrored",
                "mirror_axis": "YZ",
                "pose_dir": tmpdir,
            })
            assert result.success is True
            # Read mirrored file inside tmpdir context
            with open(result.context["pose_file"]) as fh:
                data = json.load(fh)
        # L_arm should become R_arm; translateX should be negated
        assert "R_arm" in data["objects"]
        assert data["objects"]["R_arm"]["translateX"] == -3.0
        assert data["objects"]["R_arm"]["translateY"] == 1.0

    def test_xz_mirror_negates_translateZ(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._make_pose(tmpdir, "src2", {"ctrl": {"translateZ": 5.0}})
            result = self.mod.run({
                "pose_name": "src2",
                "mirrored_pose_name": "src2_mir",
                "mirror_axis": "XZ",
                "pose_dir": tmpdir,
            })
            assert result.success is True
            with open(result.context["pose_file"]) as fh:
                data = json.load(fh)
        assert data["objects"]["ctrl"]["translateZ"] == -5.0

    def test_empty_pose_name_error(self):
        result = self.mod.run({"pose_name": "", "mirrored_pose_name": "m"})
        assert result.success is False

    def test_empty_mirrored_name_error(self):
        result = self.mod.run({"pose_name": "p", "mirrored_pose_name": ""})
        assert result.success is False

    def test_invalid_axis_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({
                "pose_name": "p",
                "mirrored_pose_name": "m",
                "mirror_axis": "XY",
                "pose_dir": tmpdir,
            })
        assert result.success is False

    def test_source_not_found_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({
                "pose_name": "nonexistent",
                "mirrored_pose_name": "mirrored",
                "pose_dir": tmpdir,
            })
        assert result.success is False


class TestDeletePose:
    def setup_method(self):
        self.mod = _load_script("maya-pose-library", "delete_pose")

    def test_basic_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "idle.pose.json")
            with open(fpath, "w") as fh:
                json.dump({"name": "idle", "objects": {}}, fh)
            result = self.mod.run({"pose_name": "idle", "pose_dir": tmpdir})
            assert result.success is True
            assert not os.path.exists(fpath)

    def test_pose_not_found_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.mod.run({"pose_name": "ghost", "pose_dir": tmpdir})
        assert result.success is False
        assert "not found" in result.message.lower() or "not found" in result.error.lower()

    def test_empty_name_error(self):
        result = self.mod.run({"pose_name": ""})
        assert result.success is False

    def test_deleted_file_reported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "run.pose.json")
            with open(fpath, "w") as fh:
                json.dump({"name": "run", "objects": {}}, fh)
            result = self.mod.run({"pose_name": "run", "pose_dir": tmpdir})
        assert "deleted_file" in result.context
