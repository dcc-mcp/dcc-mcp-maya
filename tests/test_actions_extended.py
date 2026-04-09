"""Extended tests for Maya actions — covers error paths, new primitives and materials.

All maya.cmds / maya.mel / maya.utils are mocked; no real Maya needed.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Shared Maya mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_maya():
    """Inject a minimal maya stub."""
    cmds_mock = MagicMock()
    mel_mock = MagicMock()

    # primitives
    cmds_mock.polyPlane.return_value = ["pPlane1", "polyPlane1"]
    cmds_mock.polySphere.return_value = ["pSphere1", "polySphere1"]
    cmds_mock.polyCube.return_value = ["pCube1", "polyCube1"]
    cmds_mock.polyCylinder.return_value = ["pCylinder1", "polyCylinder1"]
    cmds_mock.rename.side_effect = lambda obj, name: name
    cmds_mock.objExists.return_value = True
    cmds_mock.getAttr.return_value = [(1.0, 2.0, 3.0)]
    cmds_mock.ls.return_value = ["pSphere1", "pCube1"]
    cmds_mock.file.return_value = "/tmp/test.mb"
    cmds_mock.about.return_value = "2025"
    cmds_mock.currentUnit.return_value = "film"
    cmds_mock.upAxis.return_value = "y"

    # materials
    cmds_mock.shadingNode.return_value = "lambert1"
    cmds_mock.sets.return_value = "lambert1_SG"
    cmds_mock.objectType.return_value = "lambert"
    cmds_mock.listConnections.return_value = ["lambert1_SG"]

    with patch.dict(
        sys.modules,
        {
            "maya": MagicMock(cmds=cmds_mock, mel=mel_mock, utils=MagicMock()),
            "maya.cmds": cmds_mock,
            "maya.mel": mel_mock,
            "maya.utils": MagicMock(),
        },
    ):
        yield cmds_mock


def _reload():
    """Force reload of dcc_mcp_maya action modules."""
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]


# ---------------------------------------------------------------------------
# Helper: simulate Maya ImportError
# ---------------------------------------------------------------------------

def _no_maya_context():
    """Context manager that removes maya from sys.modules to trigger ImportError."""
    return patch.dict(sys.modules, {"maya": None, "maya.cmds": None, "maya.mel": None})


# ---------------------------------------------------------------------------
# Primitive Actions — happy path
# ---------------------------------------------------------------------------

class TestCreatePlane:
    def test_create_plane_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.primitives import create_plane

        result = create_plane()
        assert result["success"] is True
        assert result["context"]["object_name"] == "pPlane1"

    def test_create_plane_with_name(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.primitives import create_plane

        result = create_plane(width=5.0, height=5.0, name="ground")
        assert result["success"] is True
        assert result["context"]["object_name"] == "ground"
        assert result["context"]["width"] == 5.0

    def test_create_plane_exception(self, mock_maya):
        _reload()
        mock_maya.polyPlane.side_effect = RuntimeError("boom")
        from dcc_mcp_maya.actions.primitives import create_plane

        result = create_plane()
        assert result["success"] is False

    def test_create_plane_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import create_plane

            result = create_plane()
        assert result["success"] is False
        assert "Maya not available" in result["message"]


class TestGetTransform:
    def test_get_transform_success(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.primitives import get_transform

        result = get_transform("pSphere1")
        assert result["success"] is True
        assert "translate" in result["context"]
        assert "rotate" in result["context"]
        assert "scale" in result["context"]

    def test_get_transform_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.primitives import get_transform

        result = get_transform("nonexistent")
        assert result["success"] is False

    def test_get_transform_exception(self, mock_maya):
        _reload()
        mock_maya.getAttr.side_effect = RuntimeError("attr error")
        from dcc_mcp_maya.actions.primitives import get_transform

        result = get_transform("pSphere1")
        assert result["success"] is False

    def test_get_transform_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import get_transform

            result = get_transform("pSphere1")
        assert result["success"] is False
        assert "Maya not available" in result["message"]


class TestRenameObject:
    def test_rename_success(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.primitives import rename_object

        result = rename_object("pSphere1", "mySphere")
        assert result["success"] is True
        assert result["context"]["object_name"] == "mySphere"
        assert result["context"]["old_name"] == "pSphere1"

    def test_rename_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.primitives import rename_object

        result = rename_object("ghost", "newName")
        assert result["success"] is False

    def test_rename_exception(self, mock_maya):
        _reload()
        mock_maya.rename.side_effect = RuntimeError("locked")
        from dcc_mcp_maya.actions.primitives import rename_object

        result = rename_object("pSphere1", "newName")
        assert result["success"] is False

    def test_rename_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import rename_object

            result = rename_object("pSphere1", "newName")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Primitive Actions — error paths for existing actions
# ---------------------------------------------------------------------------

class TestPrimitivesErrorPaths:
    def test_create_sphere_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import create_sphere

            result = create_sphere()
        assert result["success"] is False
        assert "Maya not available" in result["message"]

    def test_create_sphere_exception(self, mock_maya):
        _reload()
        mock_maya.polySphere.side_effect = RuntimeError("gpu crash")
        from dcc_mcp_maya.actions.primitives import create_sphere

        result = create_sphere()
        assert result["success"] is False

    def test_create_cube_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import create_cube

            result = create_cube()
        assert result["success"] is False

    def test_create_cube_exception(self, mock_maya):
        _reload()
        mock_maya.polyCube.side_effect = RuntimeError("oom")
        from dcc_mcp_maya.actions.primitives import create_cube

        result = create_cube()
        assert result["success"] is False

    def test_create_cylinder_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import create_cylinder

            result = create_cylinder()
        assert result["success"] is False

    def test_create_cylinder_exception(self, mock_maya):
        _reload()
        mock_maya.polyCylinder.side_effect = RuntimeError("err")
        from dcc_mcp_maya.actions.primitives import create_cylinder

        result = create_cylinder()
        assert result["success"] is False

    def test_delete_objects_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import delete_objects

            result = delete_objects(["pSphere1"])
        assert result["success"] is False

    def test_delete_objects_exception(self, mock_maya):
        _reload()
        mock_maya.delete.side_effect = RuntimeError("locked")
        from dcc_mcp_maya.actions.primitives import delete_objects

        result = delete_objects(["pSphere1"])
        assert result["success"] is False

    def test_create_cube_with_name(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.primitives import create_cube

        result = create_cube(width=2.0, name="myCube")
        assert result["success"] is True
        assert result["context"]["object_name"] == "myCube"

    def test_create_cylinder_with_name(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.primitives import create_cylinder

        result = create_cylinder(radius=2.0, name="myCylinder")
        assert result["success"] is True
        assert result["context"]["object_name"] == "myCylinder"

    def test_delete_objects_none_existing(self, mock_maya):
        """When none of the requested objects exist, deleted list is empty."""
        _reload()
        mock_maya.ls.return_value = []
        from dcc_mcp_maya.actions.primitives import delete_objects

        result = delete_objects(["ghostObject"])
        assert result["success"] is True
        assert result["context"]["deleted"] == []

    def test_set_transform_rotate_scale(self, mock_maya):

        """Cover rotate and scale branches in set_transform."""
        _reload()
        from dcc_mcp_maya.actions.primitives import set_transform

        result = set_transform("pSphere1", rotate=[0.0, 45.0, 0.0], scale=[2.0, 2.0, 2.0])
        assert result["success"] is True
        assert "rotate" in result["context"]
        assert "scale" in result["context"]

    def test_set_transform_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.primitives import set_transform

            result = set_transform("pSphere1", translate=[0.0, 0.0, 0.0])
        assert result["success"] is False

    def test_set_transform_exception(self, mock_maya):
        _reload()
        mock_maya.setAttr.side_effect = RuntimeError("locked attr")
        from dcc_mcp_maya.actions.primitives import set_transform

        result = set_transform("pSphere1", translate=[1.0, 1.0, 1.0])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Scene Actions — error paths
# ---------------------------------------------------------------------------

class TestSceneErrorPaths:
    def test_save_scene_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import save_scene

            result = save_scene()
        assert result["success"] is False

    def test_save_scene_exception(self, mock_maya):
        _reload()
        mock_maya.file.side_effect = RuntimeError("disk full")
        from dcc_mcp_maya.actions.scene import save_scene

        result = save_scene()
        assert result["success"] is False

    def test_save_scene_with_path(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import save_scene

        result = save_scene(file_path="/tmp/myScene.mb")
        assert result["success"] is True
        mock_maya.file.assert_any_call(rename="/tmp/myScene.mb")

    def test_open_scene_success(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import open_scene

        result = open_scene("/tmp/test.mb")
        assert result["success"] is True
        assert result["context"]["file_path"] == "/tmp/test.mb"

    def test_open_scene_exception(self, mock_maya):
        _reload()
        mock_maya.file.side_effect = RuntimeError("file not found")
        from dcc_mcp_maya.actions.scene import open_scene

        result = open_scene("/nonexistent.mb")
        assert result["success"] is False

    def test_open_scene_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import open_scene

            result = open_scene("/tmp/test.mb")
        assert result["success"] is False

    def test_list_objects_with_type_filter(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import list_objects

        result = list_objects(object_type="mesh")
        assert result["success"] is True

    def test_list_objects_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import list_objects

            result = list_objects()
        assert result["success"] is False

    def test_list_objects_exception(self, mock_maya):
        _reload()
        mock_maya.ls.side_effect = RuntimeError("dag error")
        from dcc_mcp_maya.actions.scene import list_objects

        result = list_objects()
        assert result["success"] is False

    def test_get_selection_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import get_selection

            result = get_selection()
        assert result["success"] is False

    def test_get_selection_exception(self, mock_maya):
        _reload()
        mock_maya.ls.side_effect = RuntimeError("selection error")
        from dcc_mcp_maya.actions.scene import get_selection

        result = get_selection()
        assert result["success"] is False

    def test_set_selection_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import set_selection

            result = set_selection(["pSphere1"])
        assert result["success"] is False

    def test_set_selection_exception(self, mock_maya):
        _reload()
        mock_maya.select.side_effect = RuntimeError("select error")
        from dcc_mcp_maya.actions.scene import set_selection

        result = set_selection(["pSphere1"])
        assert result["success"] is False

    def test_get_session_info_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import get_session_info

            result = get_session_info()
        assert result["success"] is False

    def test_get_session_info_exception(self, mock_maya):
        _reload()
        mock_maya.about.side_effect = RuntimeError("about error")
        from dcc_mcp_maya.actions.scene import get_session_info

        result = get_session_info()
        assert result["success"] is False

    def test_new_scene_exception(self, mock_maya):
        _reload()
        mock_maya.file.side_effect = RuntimeError("new scene error")
        from dcc_mcp_maya.actions.scene import new_scene

        result = new_scene()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Scripting Actions — error paths
# ---------------------------------------------------------------------------

class TestScriptingErrorPaths:
    def test_execute_mel_no_maya(self):
        _reload()
        with patch.dict(sys.modules, {"maya": None, "maya.mel": None}):
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scripting import execute_mel

            result = execute_mel("sphere;")
        assert result["success"] is False
        assert "Maya not available" in result["message"]

    def test_execute_python_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scripting import execute_python

            result = execute_python("result = 1 + 1")
        assert result["success"] is False

    def test_execute_python_runtime_error(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scripting import execute_python

        result = execute_python("raise ValueError('oops')")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Material Actions
# ---------------------------------------------------------------------------

class TestCreateMaterial:
    def test_create_lambert_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.materials import create_material

        result = create_material()
        assert result["success"] is True
        assert result["context"]["shader_type"] == "lambert"
        assert "shading_group" in result["context"]

    def test_create_material_with_name(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.materials import create_material

        result = create_material(shader_type="blinn", name="myBlinn")
        assert result["success"] is True
        assert result["context"]["material_name"] == "myBlinn"

    def test_create_material_exception(self, mock_maya):
        _reload()
        mock_maya.shadingNode.side_effect = RuntimeError("unknown type")
        from dcc_mcp_maya.actions.materials import create_material

        result = create_material(shader_type="unknown")
        assert result["success"] is False

    def test_create_material_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.materials import create_material

            result = create_material()
        assert result["success"] is False


class TestAssignMaterial:
    def test_assign_material_via_sg(self, mock_maya):
        _reload()
        mock_maya.objectType.return_value = "shadingEngine"
        from dcc_mcp_maya.actions.materials import assign_material

        result = assign_material("lambert1_SG", ["pSphere1"])
        assert result["success"] is True

    def test_assign_material_via_material_name(self, mock_maya):
        _reload()
        mock_maya.objectType.return_value = "lambert"
        mock_maya.listConnections.return_value = ["lambert1_SG"]
        from dcc_mcp_maya.actions.materials import assign_material

        result = assign_material("lambert1", ["pSphere1"])
        assert result["success"] is True

    def test_assign_material_no_sg(self, mock_maya):
        _reload()
        mock_maya.objectType.return_value = "lambert"
        mock_maya.listConnections.return_value = []
        from dcc_mcp_maya.actions.materials import assign_material

        result = assign_material("orphanMat", ["pSphere1"])
        assert result["success"] is False

    def test_assign_material_objects_not_found(self, mock_maya):
        _reload()
        mock_maya.objectType.return_value = "shadingEngine"
        mock_maya.ls.return_value = []
        from dcc_mcp_maya.actions.materials import assign_material

        result = assign_material("lambert1_SG", ["ghost"])
        assert result["success"] is False

    def test_assign_material_exception(self, mock_maya):
        _reload()
        mock_maya.objectType.return_value = "shadingEngine"
        mock_maya.sets.side_effect = RuntimeError("assign error")
        from dcc_mcp_maya.actions.materials import assign_material

        result = assign_material("lambert1_SG", ["pSphere1"])
        assert result["success"] is False

    def test_assign_material_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.materials import assign_material

            result = assign_material("lambert1_SG", ["pSphere1"])
        assert result["success"] is False


class TestSetMaterialAttribute:
    def test_set_color(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.materials import set_material_attribute

        result = set_material_attribute("lambert1", "color", [1.0, 0.0, 0.0])
        assert result["success"] is True
        assert result["context"]["attribute"] == "color"

    def test_set_scalar_attribute(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.materials import set_material_attribute

        result = set_material_attribute("lambert1", "diffuse", 0.8)
        assert result["success"] is True

    def test_set_material_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.materials import set_material_attribute

        result = set_material_attribute("ghost", "color", [1.0, 0.0, 0.0])
        assert result["success"] is False

    def test_set_material_attribute_exception(self, mock_maya):
        _reload()
        mock_maya.setAttr.side_effect = RuntimeError("locked")
        from dcc_mcp_maya.actions.materials import set_material_attribute

        result = set_material_attribute("lambert1", "color", [1.0, 0.0, 0.0])
        assert result["success"] is False

    def test_set_material_attribute_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.materials import set_material_attribute

            result = set_material_attribute("lambert1", "color", [1.0, 0.0, 0.0])
        assert result["success"] is False


class TestListMaterials:
    def test_list_materials_all(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = ["lambert1", "blinn1"]
        from dcc_mcp_maya.actions.materials import list_materials

        result = list_materials()
        assert result["success"] is True
        assert "materials" in result["context"]

    def test_list_materials_with_type(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = ["lambert1"]
        from dcc_mcp_maya.actions.materials import list_materials

        result = list_materials(shader_type="lambert")
        assert result["success"] is True

    def test_list_materials_exception(self, mock_maya):
        _reload()
        mock_maya.ls.side_effect = RuntimeError("ls error")
        from dcc_mcp_maya.actions.materials import list_materials

        result = list_materials()
        assert result["success"] is False

    def test_list_materials_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.materials import list_materials

            result = list_materials()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Register all — updated count
# ---------------------------------------------------------------------------

class TestRegisterAllUpdated:
    def test_register_all_has_new_actions(self):
        _reload()
        from dcc_mcp_core import ActionRegistry

        from dcc_mcp_maya.actions import register_all

        reg = ActionRegistry()
        register_all(reg)
        actions = reg.list_actions()
        names = {a["name"] for a in actions}

        # new primitives
        assert "create_plane" in names
        assert "get_transform" in names
        assert "rename_object" in names

        # materials
        assert "create_material" in names
        assert "assign_material" in names
        assert "set_material_attribute" in names
        assert "list_materials" in names

        # scene hierarchy
        assert "group_objects" in names
        assert "parent_object" in names
        assert "select_by_type" in names

        # existing
        assert "create_sphere" in names
        assert "execute_mel" in names
        assert len(actions) >= 24


# ---------------------------------------------------------------------------
# Scene Hierarchy Actions
# ---------------------------------------------------------------------------

class TestGroupObjects:
    def test_group_success(self, mock_maya):
        _reload()
        mock_maya.group.return_value = "group1"
        from dcc_mcp_maya.actions.scene import group_objects

        result = group_objects(["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["group_name"] == "group1"
        assert result["context"]["count"] == 2

    def test_group_with_name(self, mock_maya):
        _reload()
        mock_maya.group.return_value = "group1"
        mock_maya.rename.side_effect = lambda obj, name: name
        from dcc_mcp_maya.actions.scene import group_objects

        result = group_objects(["pSphere1"], group_name="myGroup")
        assert result["success"] is True
        assert result["context"]["group_name"] == "myGroup"

    def test_group_world(self, mock_maya):
        _reload()
        mock_maya.group.return_value = "group1"
        from dcc_mcp_maya.actions.scene import group_objects

        result = group_objects(["pSphere1"], world=True)
        assert result["success"] is True
        mock_maya.group.assert_called_once()
        _, kwargs = mock_maya.group.call_args
        assert kwargs.get("world") is True

    def test_group_empty_list(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import group_objects

        result = group_objects([])
        assert result["success"] is False

    def test_group_objects_not_found(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = []
        from dcc_mcp_maya.actions.scene import group_objects

        result = group_objects(["ghost"])
        assert result["success"] is False

    def test_group_exception(self, mock_maya):
        _reload()
        mock_maya.group.side_effect = RuntimeError("cannot group")
        from dcc_mcp_maya.actions.scene import group_objects

        result = group_objects(["pSphere1"])
        assert result["success"] is False

    def test_group_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import group_objects

            result = group_objects(["pSphere1"])
        assert result["success"] is False


class TestParentObject:
    def test_parent_to_object(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = True
        from dcc_mcp_maya.actions.scene import parent_object

        result = parent_object("pSphere1", parent="pCube1")
        assert result["success"] is True
        assert result["context"]["child"] == "pSphere1"
        assert result["context"]["parent"] == "pCube1"

    def test_parent_to_world(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = True
        from dcc_mcp_maya.actions.scene import parent_object

        result = parent_object("pSphere1", world=True)
        assert result["success"] is True
        assert result["context"]["parent"] is None

    def test_parent_none_parent_goes_to_world(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = True
        from dcc_mcp_maya.actions.scene import parent_object

        result = parent_object("pSphere1")
        assert result["success"] is True

    def test_parent_child_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene import parent_object

        result = parent_object("ghost", parent="pCube1")
        assert result["success"] is False

    def test_parent_parent_not_found(self, mock_maya):
        _reload()
        # child exists, parent does not
        mock_maya.objExists.side_effect = lambda name: name == "pSphere1"
        from dcc_mcp_maya.actions.scene import parent_object

        result = parent_object("pSphere1", parent="ghostParent")
        assert result["success"] is False

    def test_parent_exception(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = True
        mock_maya.parent.side_effect = RuntimeError("cycle detected")
        from dcc_mcp_maya.actions.scene import parent_object

        result = parent_object("pSphere1", parent="pCube1")
        assert result["success"] is False

    def test_parent_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import parent_object

            result = parent_object("pSphere1", parent="pCube1")
        assert result["success"] is False


class TestSelectByType:
    def test_select_by_type_success(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = ["pSphere1", "pCube1"]
        from dcc_mcp_maya.actions.scene import select_by_type

        result = select_by_type("mesh")
        assert result["success"] is True
        assert result["context"]["count"] == 2
        assert result["context"]["object_type"] == "mesh"
        mock_maya.select.assert_called_once()

    def test_select_by_type_empty(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = []
        from dcc_mcp_maya.actions.scene import select_by_type

        result = select_by_type("joint")
        assert result["success"] is True
        assert result["context"]["count"] == 0
        mock_maya.select.assert_called_once_with(clear=True)

    def test_select_by_type_exception(self, mock_maya):
        _reload()
        mock_maya.ls.side_effect = RuntimeError("type error")
        from dcc_mcp_maya.actions.scene import select_by_type

        result = select_by_type("mesh")
        assert result["success"] is False

    def test_select_by_type_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import select_by_type

            result = select_by_type("mesh")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Duplicate Object
# ---------------------------------------------------------------------------

class TestDuplicateObject:
    def test_duplicate_success(self, mock_maya):
        _reload()
        mock_maya.duplicate.return_value = ["pSphere1_copy"]
        from dcc_mcp_maya.actions.scene import duplicate_object

        result = duplicate_object("pSphere1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1_copy"
        assert result["context"]["source"] == "pSphere1"
        assert result["context"]["instance"] is False

    def test_duplicate_with_name(self, mock_maya):
        _reload()
        mock_maya.duplicate.return_value = ["pSphere1_copy"]
        mock_maya.rename.side_effect = lambda obj, name: name
        from dcc_mcp_maya.actions.scene import duplicate_object

        result = duplicate_object("pSphere1", new_name="sphere_dup")
        assert result["success"] is True
        assert result["context"]["object_name"] == "sphere_dup"

    def test_duplicate_instance(self, mock_maya):
        _reload()
        mock_maya.duplicate.return_value = ["pSphere1_inst"]
        from dcc_mcp_maya.actions.scene import duplicate_object

        result = duplicate_object("pSphere1", instance=True)
        assert result["success"] is True
        assert result["context"]["instance"] is True
        _, kwargs = mock_maya.duplicate.call_args
        assert kwargs.get("instanceLeaf") is True

    def test_duplicate_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene import duplicate_object

        result = duplicate_object("ghost")
        assert result["success"] is False

    def test_duplicate_exception(self, mock_maya):
        _reload()
        mock_maya.duplicate.side_effect = RuntimeError("duplicate error")
        from dcc_mcp_maya.actions.scene import duplicate_object

        result = duplicate_object("pSphere1")
        assert result["success"] is False

    def test_duplicate_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import duplicate_object

            result = duplicate_object("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Freeze Transforms
# ---------------------------------------------------------------------------

class TestFreezeTransforms:
    def test_freeze_success(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import freeze_transforms

        result = freeze_transforms("pSphere1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"
        mock_maya.makeIdentity.assert_called_once_with(
            "pSphere1", apply=True, translate=True, rotate=True, scale=True
        )

    def test_freeze_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene import freeze_transforms

        result = freeze_transforms("ghost")
        assert result["success"] is False

    def test_freeze_exception(self, mock_maya):
        _reload()
        mock_maya.makeIdentity.side_effect = RuntimeError("locked")
        from dcc_mcp_maya.actions.scene import freeze_transforms

        result = freeze_transforms("pSphere1")
        assert result["success"] is False

    def test_freeze_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import freeze_transforms

            result = freeze_transforms("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Center Pivot
# ---------------------------------------------------------------------------

class TestCenterPivot:
    def test_center_pivot_success(self, mock_maya):
        _reload()
        mock_maya.xform.return_value = [0.0, 0.5, 0.0, 0.0, 0.5, 0.0]
        from dcc_mcp_maya.actions.scene import center_pivot

        result = center_pivot("pSphere1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"
        assert "pivot" in result["context"]

    def test_center_pivot_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene import center_pivot

        result = center_pivot("ghost")
        assert result["success"] is False

    def test_center_pivot_exception(self, mock_maya):
        _reload()
        mock_maya.xform.side_effect = RuntimeError("xform error")
        from dcc_mcp_maya.actions.scene import center_pivot

        result = center_pivot("pSphere1")
        assert result["success"] is False

    def test_center_pivot_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import center_pivot

            result = center_pivot("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Get Bounding Box
# ---------------------------------------------------------------------------

class TestGetBoundingBox:
    def test_get_bbox_success(self, mock_maya):
        _reload()
        mock_maya.exactWorldBoundingBox.return_value = [-1.0, 0.0, -1.0, 1.0, 2.0, 1.0]
        from dcc_mcp_maya.actions.scene import get_bounding_box

        result = get_bounding_box("pSphere1")
        assert result["success"] is True
        ctx = result["context"]
        assert ctx["min"] == [-1.0, 0.0, -1.0]
        assert ctx["max"] == [1.0, 2.0, 1.0]
        assert ctx["center"] == [0.0, 1.0, 0.0]
        assert ctx["size"] == [2.0, 2.0, 2.0]

    def test_get_bbox_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene import get_bounding_box

        result = get_bounding_box("ghost")
        assert result["success"] is False

    def test_get_bbox_exception(self, mock_maya):
        _reload()
        mock_maya.exactWorldBoundingBox.side_effect = RuntimeError("bbox error")
        from dcc_mcp_maya.actions.scene import get_bounding_box

        result = get_bounding_box("pSphere1")
        assert result["success"] is False

    def test_get_bbox_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import get_bounding_box

            result = get_bounding_box("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Set Visibility
# ---------------------------------------------------------------------------

class TestSetVisibility:
    def test_set_visible(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import set_visibility

        result = set_visibility("pSphere1", visible=True)
        assert result["success"] is True
        assert result["context"]["visible"] is True
        mock_maya.setAttr.assert_called_with("pSphere1.visibility", 1)

    def test_set_hidden(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import set_visibility

        result = set_visibility("pSphere1", visible=False)
        assert result["success"] is True
        assert result["context"]["visible"] is False
        mock_maya.setAttr.assert_called_with("pSphere1.visibility", 0)

    def test_set_visibility_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene import set_visibility

        result = set_visibility("ghost", visible=True)
        assert result["success"] is False

    def test_set_visibility_exception(self, mock_maya):
        _reload()
        mock_maya.setAttr.side_effect = RuntimeError("locked attr")
        from dcc_mcp_maya.actions.scene import set_visibility

        result = set_visibility("pSphere1", visible=True)
        assert result["success"] is False

    def test_set_visibility_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import set_visibility

            result = set_visibility("pSphere1", visible=True)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Lock Object
# ---------------------------------------------------------------------------

class TestLockObject:
    def test_lock_success(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import lock_object

        result = lock_object("pSphere1", lock=True)
        assert result["success"] is True
        assert result["context"]["locked"] is True
        assert mock_maya.setAttr.call_count == 9  # 9 transform attrs

    def test_unlock_success(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.scene import lock_object

        result = lock_object("pSphere1", lock=False)
        assert result["success"] is True
        assert result["context"]["locked"] is False

    def test_lock_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene import lock_object

        result = lock_object("ghost")
        assert result["success"] is False

    def test_lock_exception(self, mock_maya):
        _reload()
        mock_maya.setAttr.side_effect = RuntimeError("cannot lock")
        from dcc_mcp_maya.actions.scene import lock_object

        result = lock_object("pSphere1")
        assert result["success"] is False

    def test_lock_no_maya(self):
        _reload()
        with _no_maya_context():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.scene import lock_object

            result = lock_object("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Register all — updated count with new actions
# ---------------------------------------------------------------------------

class TestRegisterAllWithNewActions:
    def test_register_all_has_six_new_actions(self):
        _reload()
        from dcc_mcp_core import ActionRegistry

        from dcc_mcp_maya.actions import register_all

        reg = ActionRegistry()
        register_all(reg)
        actions = reg.list_actions()
        names = {a["name"] for a in actions}

        assert "duplicate_object" in names
        assert "freeze_transforms" in names
        assert "center_pivot" in names
        assert "get_bounding_box" in names
        assert "set_visibility" in names
        assert "lock_object" in names
        assert len(actions) >= 39

