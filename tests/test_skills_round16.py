"""Unit tests for Round 16 skill scripts: maya-grooming, maya-muscle, maya-fluid.

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

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
_MOD_COUNTER = [0]


def _load_script(skill_dir, script_name):
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r16_{}_{}_{}" .format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
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
    cmds_mock.listRelatives.return_value = []
    cmds_mock.pluginInfo.return_value = True
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }
    return maya_mock, cmds_mock, modules


# ---------------------------------------------------------------------------
# maya-grooming
# ---------------------------------------------------------------------------


class TestCreateGroom:
    def test_create_basic(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.igCreateGroom.return_value = "groomDescription1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "create_groom")
            result = mod.create_groom("pSphere1")
        assert result["success"] is True
        assert result["context"]["groom_node"] == "groomDescription1"
        assert result["context"]["mesh"] == "pSphere1"

    def test_create_with_name(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.igCreateGroom.return_value = "myGroom"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "create_groom")
            result = mod.create_groom("pSphere1", name="myGroom")
        assert result["success"] is True
        assert result["context"]["groom_node"] == "myGroom"

    def test_create_fur_type(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.igCreateGroom.return_value = "furDesc1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "create_groom")
            result = mod.create_groom("pCube1", description_type="fur")
        assert result["success"] is True
        assert result["context"]["description_type"] == "fur"

    def test_missing_mesh(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "create_groom")
            result = mod.create_groom("")
        assert result["success"] is False
        assert "mesh" in result["message"].lower() or "no mesh" in result["message"].lower()

    def test_invalid_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "create_groom")
            result = mod.create_groom("pSphere1", description_type="invalid")
        assert result["success"] is False
        assert "invalid" in result["message"].lower() or "description_type" in result["message"].lower()

    def test_nonexistent_mesh(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "create_groom")
            result = mod.create_groom("missing_mesh")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.igCreateGroom.side_effect = RuntimeError("xgen error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "create_groom")
            result = mod.create_groom("pSphere1")
        assert result["success"] is False
        assert "xgen error" in result["error"]


class TestListGroomables:
    def test_empty_scene(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "list_groomables")
            result = mod.list_groomables()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_groomables(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["igmGroom1", "igmGroom2"]
        cmds_mock.listRelatives.return_value = ["groomTransform1"]
        cmds_mock.listConnections.return_value = ["pSphere1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "list_groomables")
            result = mod.list_groomables()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_prompt_when_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "list_groomables")
            result = mod.list_groomables()
        assert "create_groom" in result["prompt"].lower()

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("ls fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "list_groomables")
            result = mod.list_groomables()
        assert result["success"] is False


class TestDeleteGroom:
    def test_delete_by_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "igmGroom"
        cmds_mock.listRelatives.return_value = ["groomTransform1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "delete_groom")
            result = mod.delete_groom("igmGroom1")
        assert result["success"] is True
        assert result["context"]["deleted_node"] == "igmGroom1"

    def test_delete_by_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "delete_groom")
            result = mod.delete_groom("groomTransform1")
        assert result["success"] is True

    def test_missing_node(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "delete_groom")
            result = mod.delete_groom("")
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "delete_groom")
            result = mod.delete_groom("missingGroom")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.delete.side_effect = RuntimeError("delete fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "delete_groom")
            result = mod.delete_groom("groomTransform1")
        assert result["success"] is False


class TestConvertGroomToCurves:
    def test_basic_conversion(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.igConvertGroom.return_value = ["curve1", "curve2"]
        cmds_mock.objectType.side_effect = lambda n, **kw: "transform"
        cmds_mock.group.return_value = "curveGrp1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "convert_groom_to_curves")
            result = mod.convert_groom_to_curves("groomDescription1")
        assert result["success"] is True
        assert result["context"]["curve_count"] == 2

    def test_with_group_name(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.igConvertGroom.return_value = ["curve1"]
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.group.return_value = "myGroup"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "convert_groom_to_curves")
            result = mod.convert_groom_to_curves("groomDescription1", group_name="myGroup")
        assert result["success"] is True
        assert result["context"]["curves_group"] == "myGroup"

    def test_missing_node(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "convert_groom_to_curves")
            result = mod.convert_groom_to_curves("")
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "convert_groom_to_curves")
            result = mod.convert_groom_to_curves("missingGroom")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.igConvertGroom.side_effect = RuntimeError("convert error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "convert_groom_to_curves")
            result = mod.convert_groom_to_curves("groomDescription1")
        assert result["success"] is False


class TestExportGroomCache:
    def test_basic_export(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.playbackOptions.return_value = 1.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "export_groom_cache")
            result = mod.export_groom_cache("groomDescription1", "/tmp/groom.igc")
        assert result["success"] is True
        assert result["context"]["file_path"] == "/tmp/groom.igc"

    def test_custom_frame_range(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.playbackOptions.return_value = 1.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "export_groom_cache")
            result = mod.export_groom_cache("groomDescription1", "/tmp/groom.igc", start_frame=10, end_frame=50)
        assert result["success"] is True
        assert result["context"]["frame_range"] == [10, 50]

    def test_missing_groom_node(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "export_groom_cache")
            result = mod.export_groom_cache("", "/tmp/groom.igc")
        assert result["success"] is False

    def test_missing_file_path(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "export_groom_cache")
            result = mod.export_groom_cache("groomDescription1", "")
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "export_groom_cache")
            result = mod.export_groom_cache("missing", "/tmp/groom.igc")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.playbackOptions.return_value = 1.0
        cmds_mock.igExportGroom.side_effect = RuntimeError("export error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-grooming", "export_groom_cache")
            result = mod.export_groom_cache("groomDescription1", "/tmp/groom.igc")
        assert result["success"] is False
        assert "export error" in result["error"]


# ---------------------------------------------------------------------------
# maya-muscle
# ---------------------------------------------------------------------------


class TestCreateMuscleCapsule:
    def test_basic_create(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.cMuscleObject.return_value = "cMuscleObject1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("joint1", "joint2")
        assert result["success"] is True
        assert result["context"]["muscle_node"] == "cMuscleObject1"
        assert result["context"]["start_joint"] == "joint1"

    def test_create_with_name(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.cMuscleObject.return_value = "bicep_muscle"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("joint1", "joint2", name="bicep_muscle", radius=2.0)
        assert result["success"] is True
        assert result["context"]["radius"] == 2.0

    def test_missing_joints(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("", "joint2")
        assert result["success"] is False

    def test_nonexistent_joint(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("missing_joint", "joint2")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.cMuscleObject.side_effect = RuntimeError("plugin error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "create_muscle_capsule")
            result = mod.create_muscle_capsule("joint1", "joint2")
        assert result["success"] is False
        assert "plugin error" in result["error"]


class TestListMuscles:
    def test_empty_scene(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "list_muscles")
            result = mod.list_muscles()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_muscles(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["cMuscleObject1", "cMuscleObject2"]
        cmds_mock.getAttr.return_value = 1.5
        cmds_mock.listRelatives.return_value = ["muscleTransform1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "list_muscles")
            result = mod.list_muscles()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_prompt_when_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "list_muscles")
            result = mod.list_muscles()
        assert "create_muscle_capsule" in result["prompt"].lower()

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("ls fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "list_muscles")
            result = mod.list_muscles()
        assert result["success"] is False


class TestDeleteMuscle:
    def test_delete_by_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "cMuscleObject"
        cmds_mock.listRelatives.return_value = ["muscleTransform1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "delete_muscle")
            result = mod.delete_muscle("cMuscleObject1")
        assert result["success"] is True

    def test_delete_by_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "delete_muscle")
            result = mod.delete_muscle("muscleTransform1")
        assert result["success"] is True

    def test_missing_node(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "delete_muscle")
            result = mod.delete_muscle("")
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "delete_muscle")
            result = mod.delete_muscle("missing_muscle")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.delete.side_effect = RuntimeError("delete error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "delete_muscle")
            result = mod.delete_muscle("muscleTransform1")
        assert result["success"] is False


class TestSetMuscleAttribute:
    def test_set_radius(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("cMuscleObject1", "radius", 2.0)
        assert result["success"] is True
        assert result["context"]["value"] == 2.0

    def test_set_squash(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("cMuscleObject1", "squash", 0.8)
        assert result["success"] is True

    def test_missing_args(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("", "radius", 1.0)
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("missing", "radius", 1.0)
        assert result["success"] is False

    def test_nonexistent_attribute(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("cMuscleObject1", "badAttr", 1.0)
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = True
        cmds_mock.setAttr.side_effect = RuntimeError("setAttr error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "set_muscle_attribute")
            result = mod.set_muscle_attribute("cMuscleObject1", "radius", 2.0)
        assert result["success"] is False


class TestAttachMuscleToSkin:
    def test_basic_attach(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "cMuscleSystem"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "attach_muscle_to_skin")
            result = mod.attach_muscle_to_skin("cMuscleObject1", "cMuscleSystem1")
        assert result["success"] is True
        assert result["context"]["muscle_node"] == "cMuscleObject1"
        assert result["context"]["skin_deformer"] == "cMuscleSystem1"

    def test_missing_args(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "attach_muscle_to_skin")
            result = mod.attach_muscle_to_skin("", "cMuscleSystem1")
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "attach_muscle_to_skin")
            result = mod.attach_muscle_to_skin("missing", "cMuscleSystem1")
        assert result["success"] is False

    def test_wrong_deformer_type(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "skinCluster"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "attach_muscle_to_skin")
            result = mod.attach_muscle_to_skin("cMuscleObject1", "skinCluster1")
        assert result["success"] is False
        assert "cMuscleSystem" in result["message"]

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "cMuscleSystem"
        cmds_mock.cMuscleSystem.side_effect = RuntimeError("attach error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-muscle", "attach_muscle_to_skin")
            result = mod.attach_muscle_to_skin("cMuscleObject1", "cMuscleSystem1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-fluid
# ---------------------------------------------------------------------------


class TestCreateFluidContainer:
    def test_create_3d_default(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.fluidContainer.return_value = ["fluidContainer1"]
        cmds_mock.listRelatives.return_value = ["fluidShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container()
        assert result["success"] is True
        assert result["context"]["container_type"] == "3d"

    def test_create_2d(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.fluidContainer.return_value = ["fluidContainer2D"]
        cmds_mock.listRelatives.return_value = ["fluidShape2D"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container(container_type="2d")
        assert result["success"] is True
        assert result["context"]["container_type"] == "2d"

    def test_create_with_name(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.fluidContainer.return_value = ["smokeContainer"]
        cmds_mock.listRelatives.return_value = ["smokeShape"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container(name="smokeContainer")
        assert result["success"] is True

    def test_invalid_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container(container_type="4d")
        assert result["success"] is False

    def test_invalid_resolution(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container(resolution_x=0)
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.fluidContainer.side_effect = RuntimeError("fluid error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "create_fluid_container")
            result = mod.create_fluid_container()
        assert result["success"] is False
        assert "fluid error" in result["error"]


class TestListFluidContainers:
    def test_empty_scene(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_containers(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["fluidShape1", "fluidShape2"]
        cmds_mock.listRelatives.return_value = ["fluidContainer1"]
        cmds_mock.getAttr.return_value = 10
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_prompt_when_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()
        assert "create_fluid_container" in result["prompt"].lower()

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("list error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "list_fluid_containers")
            result = mod.list_fluid_containers()
        assert result["success"] is False


class TestDeleteFluidContainer:
    def test_delete_by_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "fluidShape"
        cmds_mock.listRelatives.return_value = ["fluidContainer1"]
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("fluidShape1")
        assert result["success"] is True

    def test_delete_with_emitters(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.side_effect = [
            ["fluidShape1"],   # first call: get shapes from transform
            ["fluidEmitterTransform"],  # second call: emitter parent
        ]
        cmds_mock.listConnections.return_value = ["fluidEmitter1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("fluidContainer1", delete_emitters=True)
        assert result["success"] is True

    def test_missing_node_arg(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("")
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("missing_fluid")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "fluidShape"
        cmds_mock.listRelatives.return_value = ["fluidContainer1"]
        cmds_mock.listConnections.return_value = []
        cmds_mock.delete.side_effect = RuntimeError("delete error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "delete_fluid_container")
            result = mod.delete_fluid_container("fluidShape1")
        assert result["success"] is False


class TestSetFluidAttribute:
    def test_set_viscosity(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "viscosity", 0.5)
        assert result["success"] is True
        assert result["context"]["value"] == 0.5

    def test_set_buoyancy(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "buoyancy", 2.0)
        assert result["success"] is True

    def test_missing_args(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("", "viscosity", 0.5)
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("missing", "viscosity", 0.5)
        assert result["success"] is False

    def test_nonexistent_attribute(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "badAttr", 1.0)
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = True
        cmds_mock.setAttr.side_effect = RuntimeError("setAttr error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "set_fluid_attribute")
            result = mod.set_fluid_attribute("fluidShape1", "viscosity", 0.5)
        assert result["success"] is False


class TestAddFluidEmitter:
    def test_add_omni_emitter(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "fluidShape"
        cmds_mock.fluidEmitter.return_value = "fluidEmitter1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("fluidShape1")
        assert result["success"] is True
        assert result["context"]["emitter_node"] == "fluidEmitter1"
        assert result["context"]["emitter_type"] == "omni"

    def test_add_directional_emitter(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "fluidShape"
        cmds_mock.fluidEmitter.return_value = "fluidEmitter2"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("fluidShape1", emitter_type="directional")
        assert result["success"] is True

    def test_add_from_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = ["fluidShape1"]
        cmds_mock.fluidEmitter.return_value = "fluidEmitter3"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("fluidContainer1")
        assert result["success"] is True

    def test_missing_fluid_node(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("")
        assert result["success"] is False

    def test_invalid_emitter_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("fluidShape1", emitter_type="invalid")
        assert result["success"] is False

    def test_no_fluid_shape_child(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("nonFluidTransform")
        assert result["success"] is False

    def test_nonexistent_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("missingFluid")
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "fluidShape"
        cmds_mock.fluidEmitter.side_effect = RuntimeError("emitter error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-fluid", "add_fluid_emitter")
            result = mod.add_fluid_emitter("fluidShape1")
        assert result["success"] is False
        assert "emitter error" in result["error"]
