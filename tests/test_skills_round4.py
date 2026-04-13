"""Unit tests for Round 4 skill scripts: rigging, mesh-ops, sets, node-graph.

All tests mock maya.cmds to avoid requiring a real Maya environment.
Scripts are loaded via importlib to handle hyphenated skill directory names.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure dcc_mcp_maya.api is importable by skill scripts that use validate_node_exists
from dcc_mcp_maya import api as _maya_api

if "dcc_mcp_maya.api" not in sys.modules:
    sys.modules["dcc_mcp_maya.api"] = _maya_api

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def _load_script(skill_dir, script_name):
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r4_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    cmds_mock.objectType.return_value = "transform"
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }
    return maya_mock, cmds_mock, modules


# ---------------------------------------------------------------------------
# maya-rigging: create_joint
# ---------------------------------------------------------------------------
class TestCreateJoint:
    def test_basic_create(self):
        mod = _load_script("maya-rigging", "create_joint")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.joint.return_value = "joint1"
        with patch.dict(sys.modules, modules):
            result = mod.create_joint()
        assert result["success"] is True
        assert result["context"]["object_name"] == "joint1"

    def test_create_with_name_and_position(self):
        mod = _load_script("maya-rigging", "create_joint")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.joint.return_value = "hip_joint"
        with patch.dict(sys.modules, modules):
            result = mod.create_joint(name="hip_joint", position=[1.0, 2.0, 3.0])
        assert result["success"] is True
        assert result["context"]["position"] == [1.0, 2.0, 3.0]

    def test_create_with_parent(self):
        mod = _load_script("maya-rigging", "create_joint")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.joint.return_value = "knee_joint"
        with patch.dict(sys.modules, modules):
            result = mod.create_joint(name="knee_joint", parent="hip_joint")
        assert result["success"] is True
        assert result["context"]["parent"] == "hip_joint"

    def test_parent_not_found(self):
        mod = _load_script("maya-rigging", "create_joint")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing_parent"
        with patch.dict(sys.modules, modules):
            result = mod.create_joint(parent="missing_parent")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_invalid_position_length(self):
        mod = _load_script("maya-rigging", "create_joint")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.create_joint(position=[1.0, 2.0])
        assert result["success"] is False

    def test_main_function(self):
        mod = _load_script("maya-rigging", "create_joint")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.joint.return_value = "joint1"
        with patch.dict(sys.modules, modules):
            result = mod.main()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-rigging: create_ik_handle
# ---------------------------------------------------------------------------
class TestCreateIkHandle:
    def test_basic_create(self):
        mod = _load_script("maya-rigging", "create_ik_handle")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ikHandle.return_value = ["ikHandle1", "effector1"]
        with patch.dict(sys.modules, modules):
            result = mod.create_ik_handle(start_joint="hip", end_joint="ankle")
        assert result["success"] is True
        assert result["context"]["handle_name"] == "ikHandle1"
        assert result["context"]["effector_name"] == "effector1"

    def test_create_with_name(self):
        mod = _load_script("maya-rigging", "create_ik_handle")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ikHandle.return_value = ["leg_ik", "leg_eff"]
        with patch.dict(sys.modules, modules):
            result = mod.create_ik_handle(start_joint="hip", end_joint="ankle", name="leg_ik")
        assert result["success"] is True
        assert result["context"]["handle_name"] == "leg_ik"

    def test_start_joint_not_found(self):
        mod = _load_script("maya-rigging", "create_ik_handle")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing_joint"
        with patch.dict(sys.modules, modules):
            result = mod.create_ik_handle(start_joint="missing_joint", end_joint="ankle")
        assert result["success"] is False

    def test_end_joint_not_found(self):
        mod = _load_script("maya-rigging", "create_ik_handle")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing_ankle"
        with patch.dict(sys.modules, modules):
            result = mod.create_ik_handle(start_joint="hip", end_joint="missing_ankle")
        assert result["success"] is False

    def test_invalid_solver(self):
        mod = _load_script("maya-rigging", "create_ik_handle")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.create_ik_handle(start_joint="hip", end_joint="ankle", solver="badSolver")
        assert result["success"] is False
        assert "solver" in result["message"].lower()

    def test_sc_solver(self):
        mod = _load_script("maya-rigging", "create_ik_handle")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ikHandle.return_value = ["ik1", "eff1"]
        with patch.dict(sys.modules, modules):
            result = mod.create_ik_handle(start_joint="hip", end_joint="knee", solver="ikSCsolver")
        assert result["success"] is True
        assert result["context"]["solver"] == "ikSCsolver"


# ---------------------------------------------------------------------------
# maya-rigging: skin_cluster_bind
# ---------------------------------------------------------------------------
class TestSkinClusterBind:
    def test_basic_bind(self):
        mod = _load_script("maya-rigging", "skin_cluster_bind")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.skinCluster.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, modules):
            result = mod.skin_cluster_bind(joints=["joint1", "joint2"], mesh="pSphere1")
        assert result["success"] is True
        assert result["context"]["skin_cluster_name"] == "skinCluster1"
        assert result["context"]["joint_count"] == 2

    def test_empty_joints(self):
        mod = _load_script("maya-rigging", "skin_cluster_bind")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.skin_cluster_bind(joints=[], mesh="pSphere1")
        assert result["success"] is False
        assert "joints" in result["message"].lower()

    def test_mesh_not_found(self):
        mod = _load_script("maya-rigging", "skin_cluster_bind")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missingMesh"
        with patch.dict(sys.modules, modules):
            result = mod.skin_cluster_bind(joints=["joint1"], mesh="missingMesh")
        assert result["success"] is False

    def test_joint_not_found(self):
        mod = _load_script("maya-rigging", "skin_cluster_bind")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing_joint"
        with patch.dict(sys.modules, modules):
            result = mod.skin_cluster_bind(joints=["missing_joint"], mesh="pSphere1")
        assert result["success"] is False

    def test_with_name(self):
        mod = _load_script("maya-rigging", "skin_cluster_bind")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.skinCluster.return_value = ["body_skin"]
        with patch.dict(sys.modules, modules):
            result = mod.skin_cluster_bind(joints=["joint1"], mesh="pSphere1", name="body_skin")
        assert result["success"] is True
        assert result["context"]["skin_cluster_name"] == "body_skin"


# ---------------------------------------------------------------------------
# maya-rigging: mirror_joints
# ---------------------------------------------------------------------------
class TestMirrorJoints:
    def test_basic_mirror(self):
        mod = _load_script("maya-rigging", "mirror_joints")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.mirrorJoint.return_value = ["R_hip", "R_knee"]
        with patch.dict(sys.modules, modules):
            result = mod.mirror_joints(joint_name="L_hip")
        assert result["success"] is True
        assert "R_hip" in result["context"]["mirrored_joints"]

    def test_joint_not_found(self):
        mod = _load_script("maya-rigging", "mirror_joints")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.mirror_joints(joint_name="missing_joint")
        assert result["success"] is False

    def test_invalid_axis(self):
        mod = _load_script("maya-rigging", "mirror_joints")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.mirror_joints(joint_name="L_hip", mirror_axis="AB")
        assert result["success"] is False
        assert "axis" in result["message"].lower()

    def test_invalid_search_replace(self):
        mod = _load_script("maya-rigging", "mirror_joints")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.mirror_joints(joint_name="L_hip", search_replace=["only_one"])
        assert result["success"] is False

    def test_xy_axis(self):
        mod = _load_script("maya-rigging", "mirror_joints")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.mirrorJoint.return_value = ["R_hip"]
        with patch.dict(sys.modules, modules):
            result = mod.mirror_joints(joint_name="L_hip", mirror_axis="XY")
        assert result["success"] is True
        assert result["context"]["mirror_axis"] == "XY"


# ---------------------------------------------------------------------------
# maya-rigging: create_blend_shape
# ---------------------------------------------------------------------------
class TestCreateBlendShape:
    def test_basic_create(self):
        mod = _load_script("maya-rigging", "create_blend_shape")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.blendShape.return_value = ["blendShape1"]
        with patch.dict(sys.modules, modules):
            result = mod.create_blend_shape(base_mesh="pSphere1")
        assert result["success"] is True
        assert result["context"]["blend_shape_name"] == "blendShape1"

    def test_with_targets(self):
        mod = _load_script("maya-rigging", "create_blend_shape")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.blendShape.return_value = ["myBS"]
        with patch.dict(sys.modules, modules):
            result = mod.create_blend_shape(base_mesh="base", target_meshes=["target1", "target2"], name="myBS")
        assert result["success"] is True
        assert result["context"]["target_count"] == 2

    def test_base_not_found(self):
        mod = _load_script("maya-rigging", "create_blend_shape")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.create_blend_shape(base_mesh="missing")
        assert result["success"] is False

    def test_target_not_found(self):
        mod = _load_script("maya-rigging", "create_blend_shape")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "bad_target"
        with patch.dict(sys.modules, modules):
            result = mod.create_blend_shape(base_mesh="base", target_meshes=["bad_target"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-rigging: blend_shape_add_target
# ---------------------------------------------------------------------------
class TestBlendShapeAddTarget:
    def test_basic_add(self):
        mod = _load_script("maya-rigging", "blend_shape_add_target")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "blendShape"

        # blendShape(bs, query=True, weightCount=True) → int; geometry=True → list
        def _bs_query(bs, **kw):
            if kw.get("weightCount"):
                return 1
            if kw.get("geometry"):
                return ["pSphere1Shape"]
            return None

        cmds_mock.blendShape.side_effect = _bs_query
        with patch.dict(sys.modules, modules):
            result = mod.blend_shape_add_target(blend_shape="blendShape1", target_mesh="target1")
        assert result["success"] is True

    def test_invalid_weight(self):
        mod = _load_script("maya-rigging", "blend_shape_add_target")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.blend_shape_add_target(blend_shape="blendShape1", target_mesh="target1", weight=1.5)
        assert result["success"] is False
        assert "weight" in result["message"].lower()

    def test_blend_shape_not_found(self):
        mod = _load_script("maya-rigging", "blend_shape_add_target")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.blend_shape_add_target(blend_shape="missing", target_mesh="target1")
        assert result["success"] is False

    def test_wrong_node_type(self):
        mod = _load_script("maya-rigging", "blend_shape_add_target")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "mesh"
        with patch.dict(sys.modules, modules):
            result = mod.blend_shape_add_target(blend_shape="pSphere1", target_mesh="target1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-mesh-ops: triangulate
# ---------------------------------------------------------------------------
class TestTriangulate:
    def test_basic_triangulate(self):
        mod = _load_script("maya-mesh-ops", "triangulate")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.polyEvaluate.side_effect = lambda obj, **kw: 6 if kw.get("face") else 12
        with patch.dict(sys.modules, modules):
            result = mod.triangulate(object_name="pCube1")
        assert result["success"] is True
        assert "triangulate" in result["message"].lower()

    def test_object_not_found(self):
        mod = _load_script("maya-mesh-ops", "triangulate")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.triangulate(object_name="missing")
        assert result["success"] is False

    def test_face_count_returned(self):
        mod = _load_script("maya-mesh-ops", "triangulate")
        _, cmds_mock, modules = _make_maya_env()
        call_count = [0]

        def poly_eval(obj, **kw):
            if kw.get("face"):
                call_count[0] += 1
                return 6 if call_count[0] == 1 else 12
            return 0

        cmds_mock.polyEvaluate.side_effect = poly_eval
        with patch.dict(sys.modules, modules):
            result = mod.triangulate(object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["face_count_before"] == 6
        assert result["context"]["face_count_after"] == 12


# ---------------------------------------------------------------------------
# maya-mesh-ops: combine_meshes
# ---------------------------------------------------------------------------
class TestCombineMeshes:
    def test_basic_combine(self):
        mod = _load_script("maya-mesh-ops", "combine_meshes")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.polyUnite.return_value = ["combinedMesh"]
        with patch.dict(sys.modules, modules):
            result = mod.combine_meshes(objects=["sphere1", "cube1"])
        assert result["success"] is True
        assert result["context"]["combined_mesh"] == "combinedMesh"
        assert result["context"]["input_count"] == 2

    def test_too_few_objects(self):
        mod = _load_script("maya-mesh-ops", "combine_meshes")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.combine_meshes(objects=["sphere1"])
        assert result["success"] is False

    def test_empty_objects(self):
        mod = _load_script("maya-mesh-ops", "combine_meshes")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.combine_meshes(objects=[])
        assert result["success"] is False

    def test_object_not_found(self):
        mod = _load_script("maya-mesh-ops", "combine_meshes")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing"
        with patch.dict(sys.modules, modules):
            result = mod.combine_meshes(objects=["sphere1", "missing"])
        assert result["success"] is False

    def test_poly_unite_returns_nothing(self):
        mod = _load_script("maya-mesh-ops", "combine_meshes")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.polyUnite.return_value = []
        with patch.dict(sys.modules, modules):
            result = mod.combine_meshes(objects=["s1", "s2"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-mesh-ops: mirror_mesh
# ---------------------------------------------------------------------------
class TestMirrorMesh:
    def test_basic_mirror(self):
        mod = _load_script("maya-mesh-ops", "mirror_mesh")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.mirror_mesh(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["axis"] == "x"

    def test_invalid_axis(self):
        mod = _load_script("maya-mesh-ops", "mirror_mesh")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.mirror_mesh(object_name="pSphere1", axis="w")
        assert result["success"] is False
        assert "axis" in result["message"].lower()

    def test_empty_object_name(self):
        mod = _load_script("maya-mesh-ops", "mirror_mesh")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.mirror_mesh(object_name="")
        assert result["success"] is False

    def test_object_not_found(self):
        mod = _load_script("maya-mesh-ops", "mirror_mesh")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.mirror_mesh(object_name="missing")
        assert result["success"] is False

    def test_y_axis(self):
        mod = _load_script("maya-mesh-ops", "mirror_mesh")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.mirror_mesh(object_name="pSphere1", axis="y")
        assert result["success"] is True
        assert result["context"]["axis"] == "y"


# ---------------------------------------------------------------------------
# maya-mesh-ops: get_poly_count
# ---------------------------------------------------------------------------
class TestGetPolyCount:
    def test_single_object(self):
        mod = _load_script("maya-mesh-ops", "get_poly_count")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.polyEvaluate.side_effect = lambda obj, **kw: (
            8
            if kw.get("face")
            else 6
            if kw.get("vertex")
            else 12
            if kw.get("edge")
            else 16
            if kw.get("triangle")
            else 0
        )
        with patch.dict(sys.modules, modules):
            result = mod.get_poly_count(object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["faces"] == 8

    def test_object_not_found(self):
        mod = _load_script("maya-mesh-ops", "get_poly_count")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.get_poly_count(object_name="missing")
        assert result["success"] is False

    def test_scene_wide(self):
        mod = _load_script("maya-mesh-ops", "get_poly_count")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["mesh1", "mesh2"]
        cmds_mock.polyEvaluate.side_effect = lambda obj, **kw: 4
        with patch.dict(sys.modules, modules):
            result = mod.get_poly_count()
        assert result["success"] is True
        assert result["context"]["faces"] == 8  # 2 meshes × 4 faces

    def test_no_meshes_in_scene(self):
        mod = _load_script("maya-mesh-ops", "get_poly_count")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            result = mod.get_poly_count()
        assert result["success"] is True
        assert result["context"]["faces"] == 0


# ---------------------------------------------------------------------------
# maya-sets: create_set
# ---------------------------------------------------------------------------
class TestCreateSet:
    def test_basic_create(self):
        mod = _load_script("maya-sets", "create_set")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.sets.return_value = "mySet"
        with patch.dict(sys.modules, modules):
            result = mod.create_set(name="mySet")
        assert result["success"] is True
        assert result["context"]["set_name"] == "mySet"

    def test_create_with_objects(self):
        mod = _load_script("maya-sets", "create_set")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.sets.return_value = "rigSet"
        with patch.dict(sys.modules, modules):
            result = mod.create_set(name="rigSet", objects=["joint1", "joint2"])
        assert result["success"] is True
        assert len(result["context"]["objects_added"]) == 2

    def test_empty_name(self):
        mod = _load_script("maya-sets", "create_set")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.create_set(name="")
        assert result["success"] is False

    def test_whitespace_name(self):
        mod = _load_script("maya-sets", "create_set")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.create_set(name="   ")
        assert result["success"] is False

    def test_missing_object(self):
        mod = _load_script("maya-sets", "create_set")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missingObj"
        with patch.dict(sys.modules, modules):
            result = mod.create_set(name="s1", objects=["joint1", "missingObj"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-sets: add_to_set
# ---------------------------------------------------------------------------
class TestAddToSet:
    def test_basic_add(self):
        mod = _load_script("maya-sets", "add_to_set")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "objectSet"
        with patch.dict(sys.modules, modules):
            result = mod.add_to_set(set_name="mySet", objects=["pSphere1"])
        assert result["success"] is True
        assert result["context"]["objects_added"] == ["pSphere1"]

    def test_empty_objects(self):
        mod = _load_script("maya-sets", "add_to_set")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.add_to_set(set_name="mySet", objects=[])
        assert result["success"] is False

    def test_set_not_found(self):
        mod = _load_script("maya-sets", "add_to_set")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missingSet"
        with patch.dict(sys.modules, modules):
            result = mod.add_to_set(set_name="missingSet", objects=["pSphere1"])
        assert result["success"] is False

    def test_not_an_object_set(self):
        mod = _load_script("maya-sets", "add_to_set")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            result = mod.add_to_set(set_name="pSphere1", objects=["pCube1"])
        assert result["success"] is False
        assert "not an object set" in result["message"].lower()

    def test_object_not_found(self):
        mod = _load_script("maya-sets", "add_to_set")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "objectSet"
        cmds_mock.objExists.side_effect = lambda n: n != "missingObj"
        with patch.dict(sys.modules, modules):
            result = mod.add_to_set(set_name="mySet", objects=["missingObj"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-sets: list_sets
# ---------------------------------------------------------------------------
class TestListSets:
    def test_list_empty(self):
        mod = _load_script("maya-sets", "list_sets")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            result = mod.list_sets()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_user_sets(self):
        mod = _load_script("maya-sets", "list_sets")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["rigSet", "renderSet"]
        cmds_mock.sets.side_effect = lambda name, **kw: ["pSphere1", "pCube1"] if kw.get("query") else None
        with patch.dict(sys.modules, modules):
            result = mod.list_sets()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_filter_internal_sets(self):
        mod = _load_script("maya-sets", "list_sets")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["defaultLightSet", "rigSet"]
        cmds_mock.sets.side_effect = lambda name, **kw: [] if kw.get("query") else None
        with patch.dict(sys.modules, modules):
            result = mod.list_sets(include_internal=False)
        # defaultLightSet is internal and should be excluded
        names = [s["name"] for s in result["context"]["sets"]]
        assert "defaultLightSet" not in names
        assert "rigSet" in names

    def test_include_internal(self):
        mod = _load_script("maya-sets", "list_sets")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["defaultLightSet", "rigSet"]
        cmds_mock.sets.side_effect = lambda name, **kw: [] if kw.get("query") else None
        with patch.dict(sys.modules, modules):
            result = mod.list_sets(include_internal=True)
        names = [s["name"] for s in result["context"]["sets"]]
        assert "defaultLightSet" in names


# ---------------------------------------------------------------------------
# maya-node-graph: connect_attr
# ---------------------------------------------------------------------------
class TestConnectAttr:
    def test_basic_connect(self):
        mod = _load_script("maya-node-graph", "connect_attr")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.connect_attr(
                source_attr="pSphere1.translateX",
                dest_attr="pCube1.translateX",
            )
        assert result["success"] is True
        assert result["context"]["source_attr"] == "pSphere1.translateX"

    def test_source_not_found(self):
        mod = _load_script("maya-node-graph", "connect_attr")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing.tx"
        with patch.dict(sys.modules, modules):
            result = mod.connect_attr(source_attr="missing.tx", dest_attr="cube.tx")
        assert result["success"] is False

    def test_dest_not_found(self):
        mod = _load_script("maya-node-graph", "connect_attr")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing.tx"
        with patch.dict(sys.modules, modules):
            result = mod.connect_attr(source_attr="sphere.tx", dest_attr="missing.tx")
        assert result["success"] is False

    def test_connect_with_force(self):
        mod = _load_script("maya-node-graph", "connect_attr")
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            result = mod.connect_attr(source_attr="s.tx", dest_attr="d.tx", force=True)
        assert result["success"] is True
        cmds_mock.connectAttr.assert_called_once_with("s.tx", "d.tx", force=True)

    def test_exception_handling(self):
        mod = _load_script("maya-node-graph", "connect_attr")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.connectAttr.side_effect = RuntimeError("connection failed")
        with patch.dict(sys.modules, modules):
            result = mod.connect_attr(source_attr="s.tx", dest_attr="d.tx")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-node-graph: disconnect_attr
# ---------------------------------------------------------------------------
class TestDisconnectAttr:
    def test_basic_disconnect(self):
        mod = _load_script("maya-node-graph", "disconnect_attr")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.isConnected.return_value = True
        with patch.dict(sys.modules, modules):
            result = mod.disconnect_attr(source_attr="s.tx", dest_attr="d.tx")
        assert result["success"] is True
        cmds_mock.disconnectAttr.assert_called_once_with("s.tx", "d.tx")

    def test_source_not_found(self):
        mod = _load_script("maya-node-graph", "disconnect_attr")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "missing.tx"
        with patch.dict(sys.modules, modules):
            result = mod.disconnect_attr(source_attr="missing.tx", dest_attr="d.tx")
        assert result["success"] is False

    def test_not_connected(self):
        mod = _load_script("maya-node-graph", "disconnect_attr")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.isConnected.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.disconnect_attr(source_attr="s.tx", dest_attr="d.tx")
        assert result["success"] is False
        assert "not connected" in result["message"].lower()

    def test_exception_handling(self):
        mod = _load_script("maya-node-graph", "disconnect_attr")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.isConnected.return_value = True
        cmds_mock.disconnectAttr.side_effect = RuntimeError("error")
        with patch.dict(sys.modules, modules):
            result = mod.disconnect_attr(source_attr="s.tx", dest_attr="d.tx")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-node-graph: list_connections
# ---------------------------------------------------------------------------
class TestListConnections:
    def test_basic_list(self):
        mod = _load_script("maya-node-graph", "list_connections")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listConnections.return_value = ["s.tx", "d.tx"]
        with patch.dict(sys.modules, modules):
            result = mod.list_connections(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["connections"][0]["from"] == "s.tx"

    def test_object_not_found(self):
        mod = _load_script("maya-node-graph", "list_connections")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            result = mod.list_connections(object_name="missing")
        assert result["success"] is False

    def test_no_connections(self):
        mod = _load_script("maya-node-graph", "list_connections")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listConnections.return_value = None
        with patch.dict(sys.modules, modules):
            result = mod.list_connections(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_attribute_not_found(self):
        mod = _load_script("maya-node-graph", "list_connections")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda n: n != "pSphere1.badAttr"
        with patch.dict(sys.modules, modules):
            result = mod.list_connections(object_name="pSphere1", attribute="badAttr")
        assert result["success"] is False

    def test_with_valid_attribute(self):
        mod = _load_script("maya-node-graph", "list_connections")
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listConnections.return_value = ["a.tx", "b.tx"]
        with patch.dict(sys.modules, modules):
            result = mod.list_connections(object_name="pSphere1", attribute="translateX")
        assert result["success"] is True
