"""Round 21 - Tests for maya-expressions, maya-mocap, maya-muscle, maya-scene-assembly, maya-proxy-mesh."""

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import local modules
from dcc_mcp_maya import api as _maya_api
from tests.conftest import load_skill_script, make_mock_maya

# Ensure dcc_mcp_maya.api is importable by skill scripts that use validate_node_exists
if "dcc_mcp_maya.api" not in sys.modules:
    sys.modules["dcc_mcp_maya.api"] = _maya_api

# ===========================================================================
# maya-expressions
# ===========================================================================


class TestCreateExpression:
    def test_missing_expression(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.expression.return_value = "expression1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "create_expression")
            result = mod.create_expression("")
        assert result["success"] is False

    def test_whitespace_only_expression(self):
        mock_maya, mc, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "create_expression")
            result = mod.create_expression("   ")
        assert result["success"] is False

    def test_create_basic(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.expression.return_value = "expression1"
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "create_expression")
            result = mod.create_expression("pSphere1.tx = sin(time);")
        assert result["success"] is True
        assert result["context"]["expression_name"] == "expression1"

    def test_create_with_name(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.expression.return_value = "myExpr"
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "create_expression")
            result = mod.create_expression("pSphere1.tx = time;", name="myExpr")
        assert result["success"] is True
        assert result["context"]["node"] == "myExpr"

    def test_create_exception(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.expression.side_effect = RuntimeError("bad expr")
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "create_expression")
            result = mod.create_expression("bad;")
        assert result["success"] is False

    def test_maya_not_available(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-expressions", "create_expression")
            result = mod.create_expression("pSphere1.tx = time;")
        assert result["success"] is False

    def test_invalid_unit_conversion_type(self):
        mock_maya, mc, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "create_expression")
            result = mod.create_expression("tx = 1;", unit_conversion=99)
        assert result["success"] is False


class TestListExpressions:
    def test_list_empty(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = []
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "list_expressions")
            result = mod.list_expressions()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_nodes(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = ["expression1", "expression2"]
        mc.objExists.return_value = True
        mc.expression.side_effect = lambda node, **kw: "" if kw.get("object") else "pSphere1.tx = sin(time);"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "list_expressions")
            result = mod.list_expressions()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_list_with_filter(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = ["expression1"]
        mc.objExists.return_value = True
        mc.expression.side_effect = lambda node, **kw: "" if kw.get("object") else "pCube1.tx = 0;"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "list_expressions")
            result = mod.list_expressions(object="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_exception(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.ls.side_effect = RuntimeError("scene error")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "list_expressions")
            result = mod.list_expressions()
        assert result["success"] is False


class TestDeleteExpression:
    def test_node_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("expr1")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_delete_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.objectType.return_value = "expression"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("expr1")
        assert result["success"] is True
        assert result["context"]["expression_name"] == "expr1"
        mc.delete.assert_called_once_with("expr1")

    def test_wrong_type_fails(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.objectType.return_value = "transform"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("pSphere1")
        assert result["success"] is False

    def test_delete_exception(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.objectType.return_value = "expression"
        mc.delete.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("expr1")
        assert result["success"] is False

    def test_maya_not_available(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("expr1")
        assert result["success"] is False


class TestEditExpression:
    def test_node_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "edit_expression")
            result = mod.edit_expression("expr1", "x = 1;")
        assert result["success"] is False

    def test_edit_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.expression.return_value = "expr1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "edit_expression")
            result = mod.edit_expression("expr1", "pSphere1.ty = cos(time);")
        assert result["success"] is True
        assert result["context"]["node"] == "expr1"

    def test_edit_with_unit_conversion(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.expression.return_value = "expr1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "edit_expression")
            result = mod.edit_expression("expr1", "x = time;", unit_conversion="none")
        assert result["success"] is True

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.expression.side_effect = RuntimeError("bad syntax")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-expressions", "edit_expression")
            result = mod.edit_expression("expr1", "bad;")
        assert result["success"] is False


# ===========================================================================
# maya-mocap
# ===========================================================================


class TestImportMocap:
    def test_missing_file_path(self):
        mock_maya, mc, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "import_mocap")
            result = mod.import_mocap("")
        assert result["success"] is False

    def test_file_not_found(self, tmp_path):
        mock_maya, mc, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "import_mocap")
            result = mod.import_mocap(str(tmp_path / "nonexistent.bvh"))
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_unsupported_extension(self, tmp_path):
        mock_maya, mc, _ = make_mock_maya()
        fake_file = tmp_path / "test.abc"
        fake_file.write_text("data")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "import_mocap")
            result = mod.import_mocap(str(fake_file))
        assert result["success"] is False
        assert "Unsupported" in result["message"]

    def test_import_bvh_success(self, tmp_path):
        mock_maya, mc, _ = make_mock_maya()
        fake_file = tmp_path / "mocap.bvh"
        fake_file.write_text("HIERARCHY ROOT Hips {}")
        mc.ls.side_effect = [
            [],
            ["mocap:Hips", "mocap:Spine"],
        ]
        mc.listRelatives.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "import_mocap")
            result = mod.import_mocap(str(fake_file))
        assert result["success"] is True
        assert result["context"]["joint_count"] == 2

    def test_import_fbx_success(self, tmp_path):
        mock_maya, mc, _ = make_mock_maya()
        fake_file = tmp_path / "mocap.fbx"
        fake_file.write_text("FBX data")
        mc.ls.side_effect = [[], ["ns:Root", "ns:Hips"]]
        mc.listRelatives.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "import_mocap")
            result = mod.import_mocap(str(fake_file), namespace="ns")
        assert result["success"] is True

    def test_maya_not_available(self, tmp_path):
        fake_file = tmp_path / "mocap.bvh"
        fake_file.write_text("data")
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-mocap", "import_mocap")
            result = mod.import_mocap(str(fake_file))
        assert result["success"] is False


class TestCreateHikDefinition:
    def test_missing_character_name(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "create_hik_definition")
            result = mod.create_hik_definition("", {"Hips": "Hips"})
        assert result["success"] is False

    def test_missing_joint_mapping(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "create_hik_definition")
            result = mod.create_hik_definition("myChar", {})
        assert result["success"] is False

    def test_create_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mock_mel.eval.side_effect = lambda expr: "HIKChar1" if "hikCreateCharacter" in expr else None
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "create_hik_definition")
            result = mod.create_hik_definition("myChar", {"Hips": "Hips_jnt", "Spine": "Spine_jnt"})
        assert result["success"] is True
        assert result["context"]["mapped_count"] == 2

    def test_unknown_slot_skipped(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mock_mel.eval.side_effect = lambda expr: "HIKChar1" if "hikCreateCharacter" in expr else None
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "create_hik_definition")
            result = mod.create_hik_definition("myChar", {"Hips": "Hips_jnt", "UnknownSlot": "some_jnt"})
        assert result["success"] is True
        assert len(result["context"]["skipped"]) == 1

    def test_joint_not_found_skipped(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mock_mel.eval.side_effect = lambda expr: "HIKChar1" if "hikCreateCharacter" in expr else None
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "create_hik_definition")
            result = mod.create_hik_definition("myChar", {"Hips": "missing_jnt"})
        assert result["success"] is True
        assert result["context"]["mapped_count"] == 0


class TestBakeMocapToRig:
    def test_missing_params(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "bake_mocap_to_rig")
            result = mod.bake_mocap_to_rig("", "")
        assert result["success"] is False

    def test_no_joints_in_scene(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.ls.return_value = []
        mc.playbackOptions.return_value = 1
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "bake_mocap_to_rig")
            result = mod.bake_mocap_to_rig("src", "tgt")
        assert result["success"] is False
        assert "joints" in result["message"].lower() or "No joints" in result["message"]

    def test_bake_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.ls.return_value = ["jnt1", "jnt2"]
        mc.playbackOptions.return_value = 1
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "bake_mocap_to_rig")
            result = mod.bake_mocap_to_rig("srcChar", "tgtChar", start_frame=1, end_frame=100)
        assert result["success"] is True
        assert result["context"]["baked_joints"] == 2

    def test_default_frame_range(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.ls.return_value = ["jnt1"]
        mc.playbackOptions.return_value = 24
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-mocap", "bake_mocap_to_rig")
            result = mod.bake_mocap_to_rig("src", "tgt")
        assert result["success"] is True
        assert result["context"]["start_frame"] == 24


class TestCleanMocapKeys:
    def test_no_joints_in_scene(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "clean_mocap_keys")
            result = mod.clean_mocap_keys()
        assert result["success"] is False

    def test_clean_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = ["jnt1", "jnt2"]
        mc.objExists.return_value = True
        mc.keyframe.side_effect = [500, 120]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "clean_mocap_keys")
            result = mod.clean_mocap_keys(joints=["jnt1", "jnt2"])
        assert result["success"] is True
        assert result["context"]["keys_removed"] == 380

    def test_clean_with_frame_range(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = ["jnt1"]
        mc.objExists.return_value = True
        mc.keyframe.side_effect = [200, 80]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "clean_mocap_keys")
            result = mod.clean_mocap_keys(joints=["jnt1"], start_frame=1, end_frame=50)
        assert result["success"] is True

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = ["jnt1"]
        mc.objExists.return_value = True
        mc.keyframe.side_effect = RuntimeError("no curves")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "clean_mocap_keys")
            result = mod.clean_mocap_keys(joints=["jnt1"])
        assert result["success"] is False

    def test_joints_filtered_by_objexists(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.side_effect = lambda n: n == "jnt1"
        mc.keyframe.side_effect = [100, 40]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-mocap", "clean_mocap_keys")
            result = mod.clean_mocap_keys(joints=["jnt1", "missing_jnt"])
        assert result["success"] is True
        assert result["context"]["joints_processed"] == 1


# ===========================================================================
# maya-muscle
# ===========================================================================


class TestCreateMuscleCapsule:
    def test_missing_start_joint(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("missing_jnt", "elbow_jnt")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_create_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = ["cMuscleObject1"]
        mc.listRelatives.return_value = ["muscle_transform"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("shoulder_jnt", "elbow_jnt", radius=2.0)
        assert result["success"] is True
        assert result["context"]["radius"] == 2.0

    def test_create_with_name(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = ["cMuscleObject1"]
        mc.listRelatives.return_value = ["muscle_t"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("j1", "j2", name="bicep_muscle")
        assert result["success"] is True

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = True
        mc.loadPlugin.side_effect = RuntimeError("plugin not found")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("jnt1", "jnt2")
        assert result["success"] is False

    def test_maya_not_available(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None, "maya.mel": None}):
            mod = load_skill_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("j1", "j2")
        assert result["success"] is False


class TestListMuscles:
    def test_list_empty(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-muscle", "list_muscles")
            result = mod.list_muscles()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_nodes(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = ["cMuscleObject1", "cMuscleObject2"]
        mc.listRelatives.return_value = ["muscle_transform"]
        mc.getAttr.return_value = 1.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-muscle", "list_muscles")
            result = mod.list_muscles()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.loadPlugin.side_effect = RuntimeError("plugin error")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-muscle", "list_muscles")
            result = mod.list_muscles()
        assert result["success"] is False


class TestSetMuscleAttribute:
    def test_node_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("m1", "stiffness", 0.5)
        assert result["success"] is False

    def test_set_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("m1", "stiffness", 0.7)
        assert result["success"] is True
        mc.setAttr.assert_called_once_with("m1.stiffness", 0.7)

    def test_setattr_exception(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.setAttr.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("m1", "stiffness", 0.5)
        assert result["success"] is False

    def test_maya_not_available(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("m1", "stiffness", 0.5)
        assert result["success"] is False


class TestApplyMuscleSkin:
    def test_mesh_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "apply_muscle_skin")
            result = mod.apply_muscle_skin("pSphere1")
        assert result["success"] is False

    def test_no_muscles_available(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = True
        mc.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "apply_muscle_skin")
            result = mod.apply_muscle_skin("pSphere1")
        assert result["success"] is False
        assert "No muscle" in result["message"]

    def test_apply_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["cMuscleSystem1"]]
        mc.listRelatives.return_value = ["muscle_transform"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "apply_muscle_skin")
            result = mod.apply_muscle_skin("pSphere1", muscles=["cMuscleObject1"])
        assert result["success"] is True
        assert result["context"]["muscles_connected"] == 1

    def test_auto_discover_muscles(self):
        mock_maya, mc, _ = make_mock_maya()
        mock_mel = MagicMock()
        mc.objExists.return_value = True
        mc.ls.side_effect = [["cMuscleObject1", "cMuscleObject2"], ["cMuscleSystem1"]]
        mc.listRelatives.return_value = ["transform"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc, "maya.mel": mock_mel}):
            mod = load_skill_script("maya-muscle", "apply_muscle_skin")
            result = mod.apply_muscle_skin("pSphere1")
        assert result["success"] is True
        assert result["context"]["muscles_connected"] == 2


# ===========================================================================
# maya-scene-assembly
# ===========================================================================


class TestCreateAssemblyDefinition:
    def test_create_default(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.assembly.return_value = "assemblyDefinition1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_definition")
            result = mod.create_assembly_definition()
        assert result["success"] is True
        assert "assemblyDefinition1" in result["context"]["node"]

    def test_create_with_name(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.assembly.return_value = "myAssembly"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_definition")
            result = mod.create_assembly_definition(name="myAssembly")
        assert result["success"] is True
        assert result["context"]["node"] == "myAssembly"

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.assembly.side_effect = RuntimeError("plugin not found")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_definition")
            result = mod.create_assembly_definition()
        assert result["success"] is False

    def test_maya_not_available(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_definition")
            result = mod.create_assembly_definition()
        assert result["success"] is False


class TestAddAssemblyRepresentation:
    def test_invalid_rep_type(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "add_assembly_representation")
            result = mod.add_assembly_representation("asm1", "Invalid")
        assert result["success"] is False
        assert "Invalid" in result["message"]

    def test_assembly_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "add_assembly_representation")
            result = mod.add_assembly_representation("asm1", "Locator")
        assert result["success"] is False

    def test_add_locator_rep(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.assembly.return_value = "rep_locator"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "add_assembly_representation")
            result = mod.add_assembly_representation("asm1", "Locator", rep_name="LOD_proxy")
        assert result["success"] is True
        assert result["context"]["rep_type"] == "Locator"

    def test_add_scene_rep_with_file(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.assembly.return_value = "rep_scene"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "add_assembly_representation")
            result = mod.add_assembly_representation("asm1", "Scene", file_path="/path/to/scene.ma")
        assert result["success"] is True
        assert result["context"]["file_path"] == "/path/to/scene.ma"

    def test_all_valid_types(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.assembly.return_value = "rep_node"
        for rep_type in ("Locator", "Cache", "GPU", "Scene"):
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
                mod = load_skill_script("maya-scene-assembly", "add_assembly_representation")
                result = mod.add_assembly_representation("asm1", rep_type)
            assert result["success"] is True


class TestCreateAssemblyReference:
    def test_missing_definition(self):
        mock_maya, mc, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_reference")
            result = mod.create_assembly_reference("")
        assert result["success"] is False

    def test_create_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.assembly.return_value = "assemblyReference1"
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_reference")
            result = mod.create_assembly_reference("myAssembly")
        assert result["success"] is True
        assert result["context"]["ref_node"] == "assemblyReference1"

    def test_create_with_active_rep(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.assembly.return_value = "assemblyReference1"
        mc.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_reference")
            result = mod.create_assembly_reference("myAssembly", active_rep="LOD_high")
        assert result["success"] is True
        assert result["context"]["active_rep"] == "LOD_high"

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.assembly.side_effect = RuntimeError("plugin error")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "create_assembly_reference")
            result = mod.create_assembly_reference("myAssembly")
        assert result["success"] is False


class TestListAssemblies:
    def test_list_empty(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "list_assemblies")
            result = mod.list_assemblies()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_definitions_only(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.side_effect = lambda type=None, **kw: ["asm1"] if type == "assemblyDefinition" else []
        mc.assembly.return_value = ["Locator", "Scene"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "list_assemblies")
            result = mod.list_assemblies(node_type="definition")
        assert result["success"] is True
        assert len(result["context"]["definitions"]) == 1

    def test_list_all(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.side_effect = lambda type=None, **kw: (
            ["asm1"] if type == "assemblyDefinition" else (["ref1"] if type == "assemblyReference" else [])
        )
        mc.assembly.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "list_assemblies")
            result = mod.list_assemblies()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-scene-assembly", "list_assemblies")
            result = mod.list_assemblies()
        assert result["success"] is False


# ===========================================================================
# maya-proxy-mesh
# ===========================================================================


class TestCreateProxy:
    def test_source_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "create_proxy")
            result = mod.create_proxy("pSphere1")
        assert result["success"] is False

    def test_create_success(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.duplicate.return_value = ["pSphere1_proxy"]
        mc.listRelatives.return_value = ["pSphereShape_proxy"]
        mc.attributeQuery.return_value = False
        mc.polyEvaluate.return_value = 50
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "create_proxy")
            result = mod.create_proxy("pSphere1", reduction=90.0)
        assert result["success"] is True
        assert result["context"]["proxy"] == "pSphere1_proxy"
        assert result["context"]["source"] == "pSphere1"

    def test_custom_proxy_name(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.duplicate.return_value = ["my_proxy"]
        mc.listRelatives.return_value = []
        mc.attributeQuery.return_value = False
        mc.polyEvaluate.return_value = 10
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "create_proxy")
            result = mod.create_proxy("pSphere1", proxy_name="my_proxy")
        assert result["success"] is True
        assert result["context"]["proxy"] == "my_proxy"

    def test_reduction_clamped_above_100(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.duplicate.return_value = ["proxy1"]
        mc.listRelatives.return_value = ["proxyShape"]
        mc.attributeQuery.return_value = False
        mc.polyEvaluate.return_value = 10
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "create_proxy")
            result = mod.create_proxy("pSphere1", reduction=150.0)
        assert result["success"] is True
        assert result["context"]["reduction_percent"] == 100.0

    def test_keep_original_visible(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.duplicate.return_value = ["pSphere1_proxy"]
        mc.listRelatives.return_value = []
        mc.attributeQuery.return_value = False
        mc.polyEvaluate.return_value = 20
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "create_proxy")
            result = mod.create_proxy("pSphere1", keep_original_visible=True)
        assert result["success"] is True
        assert result["context"]["original_visible"] is True

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.duplicate.side_effect = RuntimeError("cannot duplicate")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "create_proxy")
            result = mod.create_proxy("pSphere1")
        assert result["success"] is False


class TestSwapProxy:
    def test_proxy_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "swap_proxy")
            result = mod.swap_proxy("proxy1")
        assert result["success"] is False

    def test_show_proxy_true(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = True
        mc.getAttr.side_effect = lambda attr, **kw: "pSphere1" if "proxySource" in attr else False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "swap_proxy")
            result = mod.swap_proxy("proxy1", show_proxy=True)
        assert result["success"] is True
        assert result["context"]["proxy_visible"] is True
        assert result["context"]["source_visible"] is False

    def test_show_proxy_false(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = True
        mc.getAttr.side_effect = lambda attr, **kw: "pSphere1" if "proxySource" in attr else True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "swap_proxy")
            result = mod.swap_proxy("proxy1", show_proxy=False)
        assert result["success"] is True
        assert result["context"]["proxy_visible"] is False

    def test_toggle_auto(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = False
        mc.getAttr.return_value = False  # current proxy not visible
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "swap_proxy")
            result = mod.swap_proxy("proxy1")
        assert result["success"] is True
        assert result["context"]["proxy_visible"] is True

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.attributeQuery.return_value = True
        mc.getAttr.side_effect = RuntimeError("locked attr")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "swap_proxy")
            result = mod.swap_proxy("proxy1")
        assert result["success"] is False


class TestListProxies:
    def test_list_empty(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "list_proxies")
            result = mod.list_proxies()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_with_proxies(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.return_value = ["proxy1", "proxy2", "nonProxy"]

        def mock_attr_query(attr_name, node=None, longName=None, exists=None):
            lname = longName or attr_name
            if lname == "isProxy":
                return node in ("proxy1", "proxy2")
            if lname == "proxySource":
                return node in ("proxy1", "proxy2")
            return False

        def mock_get_attr(attr, **kw):
            if "isProxy" in attr:
                return True
            if "proxySource" in attr:
                return "origMesh"
            return True

        mc.attributeQuery.side_effect = mock_attr_query
        mc.getAttr.side_effect = mock_get_attr
        mc.objExists.return_value = True
        mc.polyEvaluate.return_value = 50

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "list_proxies")
            result = mod.list_proxies()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.ls.side_effect = RuntimeError("scene error")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "list_proxies")
            result = mod.list_proxies()
        assert result["success"] is False

    def test_maya_not_available(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-proxy-mesh", "list_proxies")
            result = mod.list_proxies()
        assert result["success"] is False


class TestSetProxyAttribute:
    def test_proxy_not_found(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "set_proxy_attribute")
            result = mod.set_proxy_attribute("proxy1", "castsShadows", False)
        assert result["success"] is False

    def test_set_bool_attr(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.getAttr.return_value = "bool"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "set_proxy_attribute")
            result = mod.set_proxy_attribute("proxy1", "castsShadows", False)
        assert result["success"] is True
        mc.setAttr.assert_called_once_with("proxy1.castsShadows", False)

    def test_set_int_attr(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.getAttr.return_value = "long"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "set_proxy_attribute")
            result = mod.set_proxy_attribute("proxy1", "overrideDisplayType", 2)
        assert result["success"] is True
        mc.setAttr.assert_called_once_with("proxy1.overrideDisplayType", 2)

    def test_set_float_attr(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.getAttr.return_value = "double"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "set_proxy_attribute")
            result = mod.set_proxy_attribute("proxy1", "lodVisibility", 0.5)
        assert result["success"] is True
        mc.setAttr.assert_called_once_with("proxy1.lodVisibility", 0.5)

    def test_exception_handling(self):
        mock_maya, mc, _ = make_mock_maya()
        mc.objExists.return_value = True
        mc.getAttr.side_effect = RuntimeError("no attr")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mc}):
            mod = load_skill_script("maya-proxy-mesh", "set_proxy_attribute")
            result = mod.set_proxy_attribute("proxy1", "badAttr", 1)
        assert result["success"] is False
