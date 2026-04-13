"""Round 20: Unit tests for maya-scene, maya-primitives, maya-materials, and maya-animation skills.

These four skills lacked dedicated test coverage. Each test uses the shared
``conftest.load_skill_script`` / ``make_mock_maya`` helpers and mocks
``maya.cmds`` to run without a Maya install.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import patch

from tests.conftest import load_skill_script, make_mock_maya

# ---------------------------------------------------------------------------
# maya-scene
# ---------------------------------------------------------------------------


class TestNewScene:
    """Tests for maya-scene/scripts/new_scene.py."""

    def _load(self):
        return load_skill_script("maya-scene", "new_scene")

    def test_new_scene_success(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.new_scene()
        assert result["success"] is True
        mock_cmds.file.assert_called_once_with(new=True, force=False)

    def test_new_scene_force(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.new_scene(force=True)
        assert result["success"] is True
        mock_cmds.file.assert_called_once_with(new=True, force=True)

    def test_new_scene_no_maya(self):
        mod = self._load()
        saved = {k: sys.modules.pop(k) for k in list(sys.modules.keys()) if k == "maya" or k.startswith("maya.")}
        try:
            result = mod.new_scene()
        finally:
            sys.modules.update(saved)
        assert result["success"] is False

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestListObjects:
    """Tests for maya-scene/scripts/list_objects.py."""

    def _load(self):
        return load_skill_script("maya-scene", "list_objects")

    def test_list_all_objects(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["pSphere1", "pCube1"]
        mock_cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_objects()
        assert result["success"] is True
        assert result["context"]["count"] == 2
        # list_objects now returns SceneObject dicts (dag=True)
        obj_names = [o["name"] for o in result["context"]["objects"]]
        assert "pSphere1" in obj_names

    def test_list_by_type(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["pSphereShape1"]
        mock_cmds.objectType.return_value = "mesh"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_objects(object_type="mesh")
        assert result["success"] is True
        mock_cmds.ls.assert_called_once_with(dag=True, long=True, type="mesh")

    def test_list_empty_scene(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_objects()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestGetSelection:
    """Tests for maya-scene/scripts/get_selection.py."""

    def _load(self):
        return load_skill_script("maya-scene", "get_selection")

    def test_nothing_selected(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_selection()
        assert result["success"] is True

    def test_with_selection(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["pSphere1", "pCube1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_selection()
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestSaveScene:
    """Tests for maya-scene/scripts/save_scene.py."""

    def _load(self):
        return load_skill_script("maya-scene", "save_scene")

    def test_save_success(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.file.return_value = "/path/to/scene.ma"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.save_scene()
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.file.return_value = "/path/to/scene.ma"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-primitives
# ---------------------------------------------------------------------------


class TestCreateSphere:
    """Tests for maya-primitives/scripts/create_sphere.py."""

    def _load(self):
        return load_skill_script("maya-primitives", "create_sphere")

    def test_create_sphere_default(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.polySphere.return_value = ["pSphere1", "polySphere1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_sphere()
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"

    def test_create_sphere_with_name(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.polySphere.return_value = ["pSphere1", "polySphere1"]
        mock_cmds.rename.return_value = "mySphere"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_sphere(radius=2.0, name="mySphere")
        assert result["success"] is True
        assert result["context"]["object_name"] == "mySphere"

    def test_create_sphere_no_maya(self):
        mod = self._load()
        saved = {k: sys.modules.pop(k) for k in list(sys.modules.keys()) if k == "maya" or k.startswith("maya.")}
        try:
            result = mod.create_sphere()
        finally:
            sys.modules.update(saved)
        assert result["success"] is False

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.polySphere.return_value = ["pSphere1", "polySphere1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestCreateCube:
    """Tests for maya-primitives/scripts/create_cube.py."""

    def _load(self):
        return load_skill_script("maya-primitives", "create_cube")

    def test_create_cube_default(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.polyCube.return_value = ["pCube1", "polyCube1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_cube()
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.polyCube.return_value = ["pCube1", "polyCube1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestCreateCylinder:
    """Tests for maya-primitives/scripts/create_cylinder.py."""

    def _load(self):
        return load_skill_script("maya-primitives", "create_cylinder")

    def test_create_cylinder(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.polyCylinder.return_value = ["pCylinder1", "polyCylinder1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_cylinder()
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.polyCylinder.return_value = ["pCylinder1", "polyCylinder1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestDeleteObjects:
    """Tests for maya-primitives/scripts/delete_objects.py."""

    def _load(self):
        return load_skill_script("maya-primitives", "delete_objects")

    def test_delete_existing_objects(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["pSphere1", "pCube1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_objects(["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["deleted"] == ["pSphere1", "pCube1"]

    def test_delete_nonexistent_objects(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        # objects not found -> ls returns [] -> deleted=[] -> still success
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_objects(["ghost1"])
        assert result["success"] is True
        assert result["context"]["deleted"] == []

    def test_delete_empty_list(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_objects([])
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(object_names=["x"])
        assert isinstance(result, dict)


class TestGetTransform:
    """Tests for maya-primitives/scripts/get_transform.py."""

    def _load(self):
        return load_skill_script("maya-primitives", "get_transform")

    def test_object_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_transform("ghost")
        assert result["success"] is False

    def test_get_transform_success(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.return_value = [(1.0, 2.0, 3.0)]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_transform("pSphere1")
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(object_name="x")
        assert isinstance(result, dict)


class TestRenameObject:
    """Tests for maya-primitives/scripts/rename_object.py."""

    def _load(self):
        return load_skill_script("maya-primitives", "rename_object")

    def test_object_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.rename_object("ghost", "newName")
        assert result["success"] is False

    def test_rename_success(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.rename.return_value = "newName"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.rename_object("pSphere1", "newName")
        assert result["success"] is True
        assert result["context"]["object_name"] == "newName"

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(object_name="x", new_name="y")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-materials
# ---------------------------------------------------------------------------


class TestCreateMaterial:
    """Tests for maya-materials/scripts/create_material.py."""

    def _load(self):
        return load_skill_script("maya-materials", "create_material")

    def test_create_lambert(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.shadingNode.return_value = "lambert1"
        mock_cmds.sets.return_value = "lambert1_SG"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_material(material_type="lambert")
        assert result["success"] is True
        assert result["context"]["material_name"] == "lambert1"
        assert result["context"]["shading_group"] == "lambert1_SG"

    def test_create_with_name(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.shadingNode.return_value = "lambert1"
        mock_cmds.rename.return_value = "myMaterial"
        mock_cmds.sets.return_value = "myMaterial_SG"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_material(name="myMaterial")
        assert result["success"] is True
        assert result["context"]["material_name"] == "myMaterial"

    def test_shader_type_alias(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.shadingNode.return_value = "blinn1"
        mock_cmds.sets.return_value = "blinn1_SG"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_material(shader_type="blinn")
        assert result["success"] is True
        assert result["context"]["material_type"] == "blinn"

    def test_no_maya(self):
        mod = self._load()
        saved = {k: sys.modules.pop(k) for k in list(sys.modules.keys()) if k == "maya" or k.startswith("maya.")}
        try:
            result = mod.create_material()
        finally:
            sys.modules.update(saved)
        assert result["success"] is False

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.shadingNode.return_value = "lambert1"
        mock_cmds.sets.return_value = "lambert1_SG"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestAssignMaterial:
    """Tests for maya-materials/scripts/assign_material.py."""

    def _load(self):
        return load_skill_script("maya-materials", "assign_material")

    def test_assign_with_shading_group(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objectType.return_value = "shadingEngine"
        mock_cmds.ls.return_value = ["pSphere1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.assign_material("lambert1SG", ["pSphere1"])
        assert result["success"] is True
        assert result["context"]["shading_group"] == "lambert1SG"

    def test_assign_via_material_node(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objectType.return_value = "lambert"
        mock_cmds.listConnections.return_value = ["lambert1SG"]
        mock_cmds.ls.return_value = ["pSphere1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.assign_material("lambert1", ["pSphere1"])
        assert result["success"] is True

    def test_no_shading_group_found(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objectType.return_value = "lambert"
        mock_cmds.listConnections.return_value = []
        mock_cmds.ls.return_value = ["pSphere1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.assign_material("orphanMat", ["pSphere1"])
        assert result["success"] is False

    def test_no_objects_found(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objectType.return_value = "shadingEngine"
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.assign_material("lambert1SG", ["ghost1"])
        assert result["success"] is False

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objectType.return_value = "shadingEngine"
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(material_name="mat", objects=[])
        assert isinstance(result, dict)


class TestListMaterials:
    """Tests for maya-materials/scripts/list_materials.py."""

    def _load(self):
        return load_skill_script("maya-materials", "list_materials")

    def test_empty_scene(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_materials()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_materials(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["lambert1", "blinn1"]
        mock_cmds.objectType.return_value = "lambert"
        mock_cmds.listConnections.return_value = ["lambert1SG"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_materials()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-animation
# ---------------------------------------------------------------------------


class TestSetKeyframe:
    """Tests for maya-animation/scripts/set_keyframe.py."""

    def _load(self):
        return load_skill_script("maya-animation", "set_keyframe")

    def test_object_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_keyframe("ghost")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_set_keyframe_success(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.setKeyframe.return_value = 3
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_keyframe("pSphere1")
        assert result["success"] is True
        assert result["context"]["keyframe_count"] == 3

    def test_set_keyframe_with_attr_and_value(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.setKeyframe.return_value = 1
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_keyframe("pSphere1", attribute="translateX", value=5.0, time=10.0)
        assert result["success"] is True
        mock_cmds.setAttr.assert_called_once_with("pSphere1.translateX", 5.0)

    def test_set_keyframe_multiple_attrs(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.setKeyframe.return_value = 3
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_keyframe("pSphere1", attributes=["tx", "ty", "tz"])
        assert result["success"] is True

    def test_no_maya(self):
        mod = self._load()
        saved = {k: sys.modules.pop(k) for k in list(sys.modules.keys()) if k == "maya" or k.startswith("maya.")}
        try:
            result = mod.set_keyframe("pSphere1")
        finally:
            sys.modules.update(saved)
        assert result["success"] is False

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(object_name="x")
        assert isinstance(result, dict)


class TestGetKeyframes:
    """Tests for maya-animation/scripts/get_keyframes.py."""

    def _load(self):
        return load_skill_script("maya-animation", "get_keyframes")

    def test_object_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_keyframes("ghost")
        assert result["success"] is False

    def test_no_keyframes(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.keyframe.return_value = None
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_keyframes("pSphere1")
        assert result["success"] is True
        assert result["context"]["keyframes"] == []
        assert result["context"]["count"] == 0

    def test_with_keyframes(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.keyframe.return_value = [1.0, 5.0, 10.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_keyframes("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 3
        assert result["context"]["keyframes"] == [1.0, 5.0, 10.0]

    def test_with_attribute_filter(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.keyframe.return_value = [1.0, 5.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_keyframes("pSphere1", attribute="tx")
        assert result["success"] is True
        assert result["context"]["attribute"] == "tx"

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(object_name="x")
        assert isinstance(result, dict)


class TestSetTimeline:
    """Tests for maya-animation/scripts/set_timeline.py."""

    def _load(self):
        return load_skill_script("maya-animation", "set_timeline")

    def test_set_timeline(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_timeline(start_frame=1, end_frame=120)
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(start_frame=1, end_frame=48)
        assert isinstance(result, dict)


class TestGetCurrentTime:
    """Tests for maya-animation/scripts/get_current_time.py."""

    def _load(self):
        return load_skill_script("maya-animation", "get_current_time")

    def test_get_current_time(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.currentTime.return_value = 24.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_current_time()
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.currentTime.return_value = 1.0
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestSetCurrentTime:
    """Tests for maya-animation/scripts/set_current_time.py."""

    def _load(self):
        return load_skill_script("maya-animation", "set_current_time")

    def test_set_current_time(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_current_time(48.0)
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(frame=1.0)
        assert isinstance(result, dict)
