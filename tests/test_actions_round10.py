"""Tests for Round 10 new actions:
- references: reload_reference, unload_reference, list_namespaces
- render_layers: delete_render_layer, set_render_layer_attribute
- materials: get_shader_assignment, reset_to_default_material
- utility: create_utility_node, get_scene_statistics
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Fixture: mock Maya environment
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_maya_env(monkeypatch):
    """Inject a fully mocked maya.cmds for all tests in this module."""
    mock_cmds = MagicMock()
    maya_mock = MagicMock()
    maya_mock.cmds = mock_cmds

    monkeypatch.setitem(sys.modules, "maya", maya_mock)
    monkeypatch.setitem(sys.modules, "maya.cmds", mock_cmds)
    yield mock_cmds


# ===========================================================================
# reload_reference
# ===========================================================================


class TestReloadReference:
    def test_reload_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.referenceQuery.return_value = "/path/char.ma"

        from dcc_mcp_maya.actions.references import reload_reference

        result = reload_reference("charRN")
        assert result["success"] is True
        assert result["context"]["reference_node"] == "charRN"
        assert result["context"]["loaded"] is True
        mock_maya_env.file.assert_called_once_with(loadReference="charRN")

    def test_reload_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.references import reload_reference

        result = reload_reference("missingRN")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_reload_wrong_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "transform"

        from dcc_mcp_maya.actions.references import reload_reference

        result = reload_reference("pSphere1")
        assert result["success"] is False
        assert "not a reference" in result["message"].lower()

    def test_reload_file_query_exception(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.referenceQuery.side_effect = RuntimeError("no file")

        from dcc_mcp_maya.actions.references import reload_reference

        result = reload_reference("charRN")
        assert result["success"] is True
        assert result["context"]["file_path"] == ""

    def test_reload_raises(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.file.side_effect = RuntimeError("disk error")

        from dcc_mcp_maya.actions.references import reload_reference

        result = reload_reference("charRN")
        assert result["success"] is False

    def test_reload_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.references import reload_reference

        result = reload_reference("charRN")
        assert result["success"] is False
        assert "maya" in result["message"].lower()


# ===========================================================================
# unload_reference
# ===========================================================================


class TestUnloadReference:
    def test_unload_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"

        from dcc_mcp_maya.actions.references import unload_reference

        result = unload_reference("charRN")
        assert result["success"] is True
        assert result["context"]["loaded"] is False
        mock_maya_env.file.assert_called_once_with(unloadReference="charRN")

    def test_unload_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.references import unload_reference

        result = unload_reference("missingRN")
        assert result["success"] is False

    def test_unload_wrong_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "mesh"

        from dcc_mcp_maya.actions.references import unload_reference

        result = unload_reference("pSphereShape1")
        assert result["success"] is False
        assert "not a reference" in result["message"].lower()

    def test_unload_raises(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.file.side_effect = RuntimeError("busy")

        from dcc_mcp_maya.actions.references import unload_reference

        result = unload_reference("charRN")
        assert result["success"] is False

    def test_unload_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.references import unload_reference

        result = unload_reference("charRN")
        assert result["success"] is False


# ===========================================================================
# list_namespaces
# ===========================================================================


class TestListNamespaces:
    def test_list_all(self, mock_maya_env):
        mock_maya_env.namespaceInfo.return_value = ["char", "prop", "UI", "shared"]

        from dcc_mcp_maya.actions.references import list_namespaces

        result = list_namespaces()
        assert result["success"] is True
        ns = result["context"]["namespaces"]
        assert "char" in ns
        assert "prop" in ns
        # built-ins should be filtered out
        assert "UI" not in ns
        assert "shared" not in ns
        assert result["context"]["count"] == 2

    def test_list_root_only(self, mock_maya_env):
        mock_maya_env.namespaceInfo.return_value = ["char"]

        from dcc_mcp_maya.actions.references import list_namespaces

        result = list_namespaces(root_only=True)
        assert result["success"] is True
        mock_maya_env.namespaceInfo.assert_called_once_with(
            listOnlyNamespaces=True, recurse=False
        )

    def test_list_empty_scene(self, mock_maya_env):
        mock_maya_env.namespaceInfo.return_value = []

        from dcc_mcp_maya.actions.references import list_namespaces

        result = list_namespaces()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_raises(self, mock_maya_env):
        mock_maya_env.namespaceInfo.side_effect = RuntimeError("oops")

        from dcc_mcp_maya.actions.references import list_namespaces

        result = list_namespaces()
        assert result["success"] is False

    def test_list_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.references import list_namespaces

        result = list_namespaces()
        assert result["success"] is False


# ===========================================================================
# delete_render_layer
# ===========================================================================


class TestDeleteRenderLayer:
    def test_delete_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"
        mock_maya_env.editRenderLayerGlobals.return_value = "myLayer"

        from dcc_mcp_maya.actions.render_layers import delete_render_layer

        result = delete_render_layer("myLayer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"
        mock_maya_env.delete.assert_called_once_with("myLayer")

    def test_delete_default_layer_rejected(self, mock_maya_env):
        from dcc_mcp_maya.actions.render_layers import delete_render_layer

        result = delete_render_layer("defaultRenderLayer")
        assert result["success"] is False
        assert "protected" in result["message"].lower() or "cannot" in result["message"].lower()

    def test_delete_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.render_layers import delete_render_layer

        result = delete_render_layer("missingLayer")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_delete_wrong_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "displayLayer"

        from dcc_mcp_maya.actions.render_layers import delete_render_layer

        result = delete_render_layer("layer1")
        assert result["success"] is False
        assert "not a render layer" in result["message"].lower()

    def test_delete_switches_away_from_current(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"
        mock_maya_env.editRenderLayerGlobals.return_value = "myLayer"

        from dcc_mcp_maya.actions.render_layers import delete_render_layer

        delete_render_layer("myLayer")
        # Should have been called to switch current layer
        mock_maya_env.editRenderLayerGlobals.assert_any_call(
            currentRenderLayer="defaultRenderLayer"
        )

    def test_delete_raises(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"
        mock_maya_env.editRenderLayerGlobals.return_value = "otherLayer"
        mock_maya_env.delete.side_effect = RuntimeError("locked")

        from dcc_mcp_maya.actions.render_layers import delete_render_layer

        result = delete_render_layer("myLayer")
        assert result["success"] is False

    def test_delete_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.render_layers import delete_render_layer

        result = delete_render_layer("myLayer")
        assert result["success"] is False


# ===========================================================================
# set_render_layer_attribute
# ===========================================================================


class TestSetRenderLayerAttribute:
    def test_set_bool_renderable(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"

        from dcc_mcp_maya.actions.render_layers import set_render_layer_attribute

        result = set_render_layer_attribute("myLayer", "renderable", True)
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"
        assert result["context"]["attribute"] == "renderable"
        # bool should be converted to int(1)
        mock_maya_env.setAttr.assert_called_once_with("myLayer.renderable", 1)

    def test_set_scalar(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"

        from dcc_mcp_maya.actions.render_layers import set_render_layer_attribute

        result = set_render_layer_attribute("myLayer", "displayType", 2)
        assert result["success"] is True
        mock_maya_env.setAttr.assert_called_once_with("myLayer.displayType", 2)

    def test_set_triple(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"

        from dcc_mcp_maya.actions.render_layers import set_render_layer_attribute

        result = set_render_layer_attribute("myLayer", "color", [1.0, 0.0, 0.0])
        assert result["success"] is True
        mock_maya_env.setAttr.assert_called_once_with(
            "myLayer.color", 1.0, 0.0, 0.0, type="double3"
        )

    def test_set_layer_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.render_layers import set_render_layer_attribute

        result = set_render_layer_attribute("missing", "renderable", True)
        assert result["success"] is False

    def test_set_wrong_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "displayLayer"

        from dcc_mcp_maya.actions.render_layers import set_render_layer_attribute

        result = set_render_layer_attribute("dispLayer", "renderable", True)
        assert result["success"] is False

    def test_set_raises(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"
        mock_maya_env.setAttr.side_effect = RuntimeError("locked attr")

        from dcc_mcp_maya.actions.render_layers import set_render_layer_attribute

        result = set_render_layer_attribute("myLayer", "renderable", False)
        assert result["success"] is False

    def test_set_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.render_layers import set_render_layer_attribute

        result = set_render_layer_attribute("myLayer", "renderable", True)
        assert result["success"] is False


# ===========================================================================
# get_shader_assignment
# ===========================================================================


class TestGetShaderAssignment:
    def test_get_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.listRelatives.return_value = ["|pSphere1|pSphereShape1"]
        mock_maya_env.listConnections.side_effect = [
            ["blinn1SG"],       # shadingEngine connections
            ["blinn1"],         # surfaceShader connections
        ]

        from dcc_mcp_maya.actions.materials import get_shader_assignment

        result = get_shader_assignment("pSphere1")
        assert result["success"] is True
        sgs = result["context"]["shading_groups"]
        assert len(sgs) == 1
        assert sgs[0]["shading_group"] == "blinn1SG"
        assert sgs[0]["material"] == "blinn1"

    def test_get_no_shapes_fallback(self, mock_maya_env):
        """If listRelatives returns nothing, fall back to object_name itself."""
        mock_maya_env.objExists.return_value = True
        mock_maya_env.listRelatives.return_value = []
        mock_maya_env.listConnections.side_effect = [
            ["lambert1SG"],
            ["lambert1"],
        ]

        from dcc_mcp_maya.actions.materials import get_shader_assignment

        result = get_shader_assignment("pSphere1")
        assert result["success"] is True

    def test_get_object_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.materials import get_shader_assignment

        result = get_shader_assignment("ghost")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_get_no_sg(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.listRelatives.return_value = ["|pSphere1|pSphereShape1"]
        mock_maya_env.listConnections.return_value = []

        from dcc_mcp_maya.actions.materials import get_shader_assignment

        result = get_shader_assignment("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_get_deduplicates_sgs(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.listRelatives.return_value = [
            "|pSphere1|pSphereShape1",
            "|pSphere1|pSphereShape2",
        ]
        # Both shapes reference the same SG
        mock_maya_env.listConnections.side_effect = [
            ["blinn1SG"],
            ["blinn1"],
            ["blinn1SG"],  # duplicate
        ]

        from dcc_mcp_maya.actions.materials import get_shader_assignment

        result = get_shader_assignment("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_get_raises(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.listRelatives.side_effect = RuntimeError("bad node")

        from dcc_mcp_maya.actions.materials import get_shader_assignment

        result = get_shader_assignment("pSphere1")
        assert result["success"] is False

    def test_get_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.materials import get_shader_assignment

        result = get_shader_assignment("pSphere1")
        assert result["success"] is False


# ===========================================================================
# reset_to_default_material
# ===========================================================================


class TestResetToDefaultMaterial:
    def test_reset_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True

        from dcc_mcp_maya.actions.materials import reset_to_default_material

        result = reset_to_default_material("pSphere1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"
        assert result["context"]["shading_group"] == "initialShadingGroup"
        assert result["context"]["material"] == "lambert1"
        mock_maya_env.sets.assert_called_once_with(
            "pSphere1", edit=True, forceElement="initialShadingGroup"
        )

    def test_reset_object_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.materials import reset_to_default_material

        result = reset_to_default_material("ghost")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_reset_raises(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.sets.side_effect = RuntimeError("locked")

        from dcc_mcp_maya.actions.materials import reset_to_default_material

        result = reset_to_default_material("pSphere1")
        assert result["success"] is False

    def test_reset_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.materials import reset_to_default_material

        result = reset_to_default_material("pSphere1")
        assert result["success"] is False


# ===========================================================================
# create_utility_node
# ===========================================================================


class TestCreateUtilityNode:
    def test_create_success(self, mock_maya_env):
        mock_maya_env.shadingNode.return_value = "multiplyDivide1"

        from dcc_mcp_maya.actions.utility import create_utility_node

        result = create_utility_node("multiplyDivide")
        assert result["success"] is True
        assert result["context"]["node_type"] == "multiplyDivide"
        mock_maya_env.shadingNode.assert_called_once_with("multiplyDivide", asUtility=True)

    def test_create_with_name(self, mock_maya_env):
        mock_maya_env.shadingNode.return_value = "multiplyDivide1"
        mock_maya_env.rename.return_value = "md_speed"

        from dcc_mcp_maya.actions.utility import create_utility_node

        result = create_utility_node("multiplyDivide", name="md_speed")
        assert result["success"] is True
        assert result["context"]["node_name"] == "md_speed"
        mock_maya_env.rename.assert_called_once_with("multiplyDivide1", "md_speed")

    def test_create_empty_type(self, mock_maya_env):
        from dcc_mcp_maya.actions.utility import create_utility_node

        result = create_utility_node("")
        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_create_raises(self, mock_maya_env):
        mock_maya_env.shadingNode.side_effect = RuntimeError("unknown type")

        from dcc_mcp_maya.actions.utility import create_utility_node

        result = create_utility_node("badNodeType")
        assert result["success"] is False

    def test_create_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.utility import create_utility_node

        result = create_utility_node("multiplyDivide")
        assert result["success"] is False

    def test_create_condition_node(self, mock_maya_env):
        mock_maya_env.shadingNode.return_value = "condition1"

        from dcc_mcp_maya.actions.utility import create_utility_node

        result = create_utility_node("condition")
        assert result["success"] is True
        assert result["context"]["node_name"] == "condition1"

    def test_create_blank_name_ignored(self, mock_maya_env):
        """A name that is only whitespace should be treated as no name."""
        mock_maya_env.shadingNode.return_value = "reverse1"

        from dcc_mcp_maya.actions.utility import create_utility_node

        result = create_utility_node("reverse", name="  ")
        assert result["success"] is True
        mock_maya_env.rename.assert_not_called()


# ===========================================================================
# get_scene_statistics
# ===========================================================================


class TestGetSceneStatistics:
    def _setup_mock(self, mock_maya_env):
        """Configure common mock return values."""
        mock_maya_env.ls.side_effect = lambda **kw: {
            "type": {
                "transform": ["pSphere1", "pCube1", "camera1"],
                "mesh": ["pSphereShape1", "pCubeShape1"],
                "file": ["file1"],
                "camera": ["cameraShape1"],
                "pointLight": ["pointLight1"],
                "directionalLight": [],
                "spotLight": [],
                "areaLight": [],
                "ambientLight": [],
                "aiAreaLight": [],
                "aiSkyDomeLight": [],
            }.get(kw.get("type"), ["node1", "node2", "node3"])
        }.get("type", ["node1", "node2", "node3"]) if kw else ["node1", "node2", "node3"]
        mock_maya_env.polyEvaluate.side_effect = lambda mesh, **kw: (
            100 if kw.get("vertex") else 50 if kw.get("face") else 0
        )
        mock_maya_env.file.return_value = "/scene/test.ma"

    def test_returns_statistics_dict(self, mock_maya_env):
        # Simple setup: ls() without args returns all nodes
        mock_maya_env.ls.return_value = ["node1", "node2", "node3", "node4"]
        mock_maya_env.polyEvaluate.return_value = 0
        mock_maya_env.file.return_value = "/scene/test.ma"

        from dcc_mcp_maya.actions.utility import get_scene_statistics

        result = get_scene_statistics()
        assert result["success"] is True
        ctx = result["context"]
        assert "total_nodes" in ctx
        assert "mesh_count" in ctx
        assert "poly_vertex_count" in ctx
        assert "poly_face_count" in ctx
        assert "texture_count" in ctx
        assert "camera_count" in ctx
        assert "light_count" in ctx
        assert "scene_file" in ctx

    def test_empty_scene(self, mock_maya_env):
        mock_maya_env.ls.return_value = []
        mock_maya_env.polyEvaluate.return_value = 0
        mock_maya_env.file.return_value = ""

        from dcc_mcp_maya.actions.utility import get_scene_statistics

        result = get_scene_statistics()
        assert result["success"] is True
        assert result["context"]["total_nodes"] == 0

    def test_poly_evaluate_exception_handled(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["mesh1"]
        mock_maya_env.polyEvaluate.side_effect = RuntimeError("no mesh")
        mock_maya_env.file.return_value = ""

        from dcc_mcp_maya.actions.utility import get_scene_statistics

        # Should not raise; poly counts remain 0
        result = get_scene_statistics()
        assert result["success"] is True
        assert result["context"]["poly_vertex_count"] == 0

    def test_scene_file_exception_handled(self, mock_maya_env):
        mock_maya_env.ls.return_value = []
        mock_maya_env.polyEvaluate.return_value = 0
        mock_maya_env.file.side_effect = RuntimeError("no scene")

        from dcc_mcp_maya.actions.utility import get_scene_statistics

        result = get_scene_statistics()
        assert result["success"] is True
        assert result["context"]["scene_file"] == ""

    def test_raises(self, mock_maya_env):
        mock_maya_env.ls.side_effect = RuntimeError("fatal")

        from dcc_mcp_maya.actions.utility import get_scene_statistics

        result = get_scene_statistics()
        assert result["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.utility import get_scene_statistics

        result = get_scene_statistics()
        assert result["success"] is False


# ===========================================================================
# register_all sanity check for Round 10
# ===========================================================================


class TestRegisterAllRound10:
    def test_all_new_actions_in_registry(self, mock_maya_env):
        from dcc_mcp_maya.actions import __all__

        new_actions = [
            "reload_reference",
            "unload_reference",
            "list_namespaces",
            "delete_render_layer",
            "set_render_layer_attribute",
            "get_shader_assignment",
            "reset_to_default_material",
            "create_utility_node",
            "get_scene_statistics",
        ]
        for action in new_actions:
            assert action in __all__, "{} not in __all__".format(action)

    def test_total_action_count(self, mock_maya_env):
        from dcc_mcp_maya.actions import __all__

        assert len(__all__) >= 98, "Expected at least 98 actions, got {}".format(len(__all__))
