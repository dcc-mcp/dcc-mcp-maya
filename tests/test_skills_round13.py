"""Round-13 tests: maya-xgen, maya-mash, maya-selection skill scripts.

All tests use importlib to load scripts from hyphenated directories and
mock both maya.cmds and the third-party XGen/MASH Python APIs.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir, script_name):
    """Dynamically load a skill script from a hyphenated directory."""
    path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location("{}_{}".format(skill_dir.replace("-", "_"), script_name), str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_mock_maya():
    """Return a mock maya module with .cmds pre-wired."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.api"] = MagicMock()
    sys.modules["maya.utils"] = MagicMock()
    return mock_cmds


def _cleanup_maya():
    for mod in ("maya", "maya.cmds", "maya.api", "maya.utils"):
        sys.modules.pop(mod, None)


# ---------------------------------------------------------------------------
# maya-xgen
# ---------------------------------------------------------------------------
class TestXgenCreateDescription:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.objExists.return_value = True
        self.mock_xg = MagicMock()
        self.mock_xg.createPalette.return_value = "xgenCollection1"
        self.mock_xg.createDescription.return_value = "description1"
        sys.modules["xgenm"] = self.mock_xg

    def teardown_method(self):
        _cleanup_maya()
        sys.modules.pop("xgenm", None)

    def test_create_success(self):
        mod = _load_script("maya-xgen", "create_description")
        result = mod.run({"mesh": "pSphere1"})
        assert result["success"] is True
        assert "description1" in result["message"]

    def test_missing_mesh_param(self):
        mod = _load_script("maya-xgen", "create_description")
        result = mod.run({})
        assert result["success"] is False
        assert "mesh" in result["error"].lower()

    def test_mesh_not_exists(self):
        self.mock_cmds.objExists.return_value = False
        mod = _load_script("maya-xgen", "create_description")
        result = mod.run({"mesh": "nonexistent"})
        assert result["success"] is False
        assert "not exist" in result["error"]

    def test_custom_primitive(self):
        mod = _load_script("maya-xgen", "create_description")
        result = mod.run({"mesh": "pSphere1", "primitive": "CardPrimitive"})
        assert result["success"] is True
        assert result["context"]["primitive"] == "CardPrimitive"

    def test_exception(self):
        self.mock_xg.createPalette.side_effect = RuntimeError("plugin not loaded")
        mod = _load_script("maya-xgen", "create_description")
        result = mod.run({"mesh": "pSphere1"})
        assert result["success"] is False
        assert "plugin not loaded" in result["error"]

    def test_prompt_present(self):
        mod = _load_script("maya-xgen", "create_description")
        result = mod.run({"mesh": "pSphere1"})
        assert result["prompt"] is not None and len(result["prompt"]) > 0


class TestXgenListDescriptions:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_xg = MagicMock()
        self.mock_xg.palettes.return_value = ["xgenCollection1"]
        self.mock_xg.descriptions.return_value = ["description1", "description2"]
        self.mock_xg.boundGeometry.return_value = ["pSphere1"]
        sys.modules["xgenm"] = self.mock_xg

    def teardown_method(self):
        _cleanup_maya()
        sys.modules.pop("xgenm", None)

    def test_list_all(self):
        mod = _load_script("maya-xgen", "list_descriptions")
        result = mod.run({})
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_collection_filter(self):
        mod = _load_script("maya-xgen", "list_descriptions")
        result = mod.run({"collection": "xgenCollection1"})
        assert result["success"] is True

    def test_collection_filter_excludes(self):
        mod = _load_script("maya-xgen", "list_descriptions")
        result = mod.run({"collection": "otherCollection"})
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_exception(self):
        self.mock_xg.palettes.side_effect = RuntimeError("xgen error")
        mod = _load_script("maya-xgen", "list_descriptions")
        result = mod.run({})
        assert result["success"] is False


class TestXgenDeleteDescription:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_xg = MagicMock()
        self.mock_xg.descriptions.return_value = ["description1"]
        sys.modules["xgenm"] = self.mock_xg

    def teardown_method(self):
        _cleanup_maya()
        sys.modules.pop("xgenm", None)

    def test_delete_success(self):
        mod = _load_script("maya-xgen", "delete_description")
        result = mod.run({"collection": "col1", "description": "description1"})
        assert result["success"] is True
        self.mock_xg.deleteDescription.assert_called_once_with("col1", "description1")

    def test_missing_params(self):
        mod = _load_script("maya-xgen", "delete_description")
        result = mod.run({"collection": "col1"})
        assert result["success"] is False

    def test_description_not_found(self):
        self.mock_xg.descriptions.return_value = []
        mod = _load_script("maya-xgen", "delete_description")
        result = mod.run({"collection": "col1", "description": "missing"})
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_exception(self):
        self.mock_xg.deleteDescription.side_effect = RuntimeError("delete error")
        mod = _load_script("maya-xgen", "delete_description")
        result = mod.run({"collection": "col1", "description": "description1"})
        assert result["success"] is False


class TestXgenSetAttribute:
    def setup_method(self):
        _make_mock_maya()
        self.mock_xg = MagicMock()
        sys.modules["xgenm"] = self.mock_xg

    def teardown_method(self):
        _cleanup_maya()
        sys.modules.pop("xgenm", None)

    def test_set_success(self):
        mod = _load_script("maya-xgen", "set_xgen_attribute")
        result = mod.run({"collection": "c", "description": "d", "attribute": "density", "value": "5.0"})
        assert result["success"] is True
        self.mock_xg.setAttr.assert_called_once_with("density", "5.0", "c", "d", "")

    def test_missing_params(self):
        mod = _load_script("maya-xgen", "set_xgen_attribute")
        result = mod.run({"collection": "c"})
        assert result["success"] is False

    def test_exception(self):
        self.mock_xg.setAttr.side_effect = RuntimeError("attr error")
        mod = _load_script("maya-xgen", "set_xgen_attribute")
        result = mod.run({"collection": "c", "description": "d", "attribute": "density", "value": "3"})
        assert result["success"] is False

    def test_value_coerced_to_string(self):
        mod = _load_script("maya-xgen", "set_xgen_attribute")
        result = mod.run({"collection": "c", "description": "d", "attribute": "density", "value": 42})
        assert result["success"] is True
        assert result["context"]["value"] == "42"


class TestXgenGetAttribute:
    def setup_method(self):
        _make_mock_maya()
        self.mock_xg = MagicMock()
        self.mock_xg.getAttr.return_value = "5.0"
        sys.modules["xgenm"] = self.mock_xg

    def teardown_method(self):
        _cleanup_maya()
        sys.modules.pop("xgenm", None)

    def test_get_success(self):
        mod = _load_script("maya-xgen", "get_xgen_attribute")
        result = mod.run({"collection": "c", "description": "d", "attribute": "density"})
        assert result["success"] is True
        assert result["context"]["value"] == "5.0"

    def test_missing_params(self):
        mod = _load_script("maya-xgen", "get_xgen_attribute")
        result = mod.run({"collection": "c"})
        assert result["success"] is False

    def test_exception(self):
        self.mock_xg.getAttr.side_effect = RuntimeError("get error")
        mod = _load_script("maya-xgen", "get_xgen_attribute")
        result = mod.run({"collection": "c", "description": "d", "attribute": "density"})
        assert result["success"] is False

    def test_prompt_present(self):
        mod = _load_script("maya-xgen", "get_xgen_attribute")
        result = mod.run({"collection": "c", "description": "d", "attribute": "density"})
        assert result["prompt"] is not None


# ---------------------------------------------------------------------------
# maya-mash
# ---------------------------------------------------------------------------
def _make_mash_mock():
    """Create a MASH mock where sys.modules['MASH'].api == sys.modules['MASH.api']."""
    mock_mapi = MagicMock()
    mock_mash = MagicMock()
    mock_mash.api = mock_mapi
    sys.modules["MASH"] = mock_mash
    sys.modules["MASH.api"] = mock_mapi
    return mock_mapi


def _cleanup_mash():
    sys.modules.pop("MASH", None)
    sys.modules.pop("MASH.api", None)


class TestMashCreateNetwork:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.objExists.return_value = True
        self.mock_mapi = _make_mash_mock()
        mock_network_inst = MagicMock()
        mock_network_inst.meshName = "MASH1_Instancer"
        mock_network_inst.instancer = "MASH1_Instancer"
        mock_network_inst.waiter = "MASH1_Waiter"
        self.mock_mapi.Network.return_value = mock_network_inst
        self.mock_net = mock_network_inst

    def teardown_method(self):
        _cleanup_maya()
        _cleanup_mash()

    def test_create_success(self):
        mod = _load_script("maya-mash", "create_network")
        result = mod.run({"object_name": "pSphere1"})
        assert result["success"] is True
        assert "MASH1_Instancer" in result["message"] or result["context"].get("network_name")

    def test_missing_object_name(self):
        mod = _load_script("maya-mash", "create_network")
        result = mod.run({})
        assert result["success"] is False
        assert "object_name" in result["error"]

    def test_object_not_exists(self):
        self.mock_cmds.objExists.return_value = False
        mod = _load_script("maya-mash", "create_network")
        result = mod.run({"object_name": "nonexistent"})
        assert result["success"] is False

    def test_custom_network_name(self):
        mod = _load_script("maya-mash", "create_network")
        result = mod.run({"object_name": "pSphere1", "network_name": "myMASH"})
        assert result["success"] is True

    def test_exception(self):
        self.mock_net.createNetwork.side_effect = RuntimeError("MASH not loaded")
        mod = _load_script("maya-mash", "create_network")
        result = mod.run({"object_name": "pSphere1"})
        assert result["success"] is False


class TestMashListNetworks:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.ls.return_value = ["MASH1_Waiter", "MASH2_Waiter"]
        self.mock_cmds.listConnections.return_value = ["MASH1_Instancer"]
        sys.modules.pop("MASH", None)
        sys.modules.pop("MASH.api", None)

    def teardown_method(self):
        _cleanup_maya()

    def test_list_networks(self):
        mod = _load_script("maya-mash", "list_networks")
        result = mod.run({})
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_empty_scene(self):
        self.mock_cmds.ls.return_value = []
        mod = _load_script("maya-mash", "list_networks")
        result = mod.run({})
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_exception(self):
        self.mock_cmds.ls.side_effect = RuntimeError("cmds error")
        mod = _load_script("maya-mash", "list_networks")
        result = mod.run({})
        assert result["success"] is False


class TestMashDeleteNetwork:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.objExists.return_value = True
        self.mock_mapi = _make_mash_mock()
        self.mock_net = MagicMock()
        self.mock_mapi.Network.return_value = self.mock_net

    def teardown_method(self):
        _cleanup_maya()
        _cleanup_mash()

    def test_delete_success(self):
        mod = _load_script("maya-mash", "delete_network")
        result = mod.run({"waiter": "MASH1_Waiter"})
        assert result["success"] is True

    def test_missing_waiter(self):
        mod = _load_script("maya-mash", "delete_network")
        result = mod.run({})
        assert result["success"] is False

    def test_waiter_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = _load_script("maya-mash", "delete_network")
        result = mod.run({"waiter": "missing"})
        assert result["success"] is False

    def test_exception(self):
        self.mock_net.deleteNetwork.side_effect = RuntimeError("delete error")
        mod = _load_script("maya-mash", "delete_network")
        result = mod.run({"waiter": "MASH1_Waiter"})
        assert result["success"] is False


class TestMashAddNode:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.objExists.return_value = True
        self.mock_mapi = _make_mash_mock()
        mock_net = MagicMock()
        mock_net.addNode.return_value = "MASH1_Random1"
        self.mock_mapi.Network.return_value = mock_net
        self.mock_net = mock_net

    def teardown_method(self):
        _cleanup_maya()
        _cleanup_mash()

    def test_add_success(self):
        mod = _load_script("maya-mash", "add_node")
        result = mod.run({"waiter": "MASH1_Waiter", "node_type": "MASH_Random"})
        assert result["success"] is True
        assert result["context"]["node_name"] == "MASH1_Random1"

    def test_missing_params(self):
        mod = _load_script("maya-mash", "add_node")
        result = mod.run({"waiter": "MASH1_Waiter"})
        assert result["success"] is False

    def test_waiter_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = _load_script("maya-mash", "add_node")
        result = mod.run({"waiter": "missing", "node_type": "MASH_Random"})
        assert result["success"] is False

    def test_exception(self):
        self.mock_net.addNode.side_effect = RuntimeError("add error")
        mod = _load_script("maya-mash", "add_node")
        result = mod.run({"waiter": "MASH1_Waiter", "node_type": "MASH_Random"})
        assert result["success"] is False


class TestMashSetAttribute:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.objExists.return_value = True

    def teardown_method(self):
        _cleanup_maya()

    def test_set_success(self):
        mod = _load_script("maya-mash", "set_mash_attribute")
        result = mod.run({"node": "MASH1_Random", "attribute": "amplitudeX", "value": 2.0})
        assert result["success"] is True
        self.mock_cmds.setAttr.assert_called_once_with("MASH1_Random.amplitudeX", 2.0)

    def test_missing_params(self):
        mod = _load_script("maya-mash", "set_mash_attribute")
        result = mod.run({"node": "MASH1_Random"})
        assert result["success"] is False

    def test_node_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = _load_script("maya-mash", "set_mash_attribute")
        result = mod.run({"node": "missing", "attribute": "amplitudeX", "value": 1.0})
        assert result["success"] is False

    def test_exception(self):
        self.mock_cmds.setAttr.side_effect = RuntimeError("setAttr error")
        mod = _load_script("maya-mash", "set_mash_attribute")
        result = mod.run({"node": "MASH1_Random", "attribute": "amplitudeX", "value": 1.0})
        assert result["success"] is False

    def test_prompt_present(self):
        mod = _load_script("maya-mash", "set_mash_attribute")
        result = mod.run({"node": "MASH1_Random", "attribute": "amplitudeX", "value": 1.0})
        assert result["prompt"] is not None


# ---------------------------------------------------------------------------
# maya-selection
# ---------------------------------------------------------------------------
class TestSelectionGrow:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.ls.side_effect = [
            ["pSphere1.f[0]", "pSphere1.f[1]"],  # before
            ["pSphere1.f[0]", "pSphere1.f[1]", "pSphere1.f[2]", "pSphere1.f[3]"],  # after
        ]

    def teardown_method(self):
        _cleanup_maya()

    def test_grow_success(self):
        mod = _load_script("maya-selection", "grow_selection")
        result = mod.run({})
        assert result["success"] is True
        assert result["context"]["added"] == 2

    def test_grow_calls_command(self):
        mod = _load_script("maya-selection", "grow_selection")
        mod.run({})
        self.mock_cmds.GrowPolygonSelectionRegion.assert_called_once()

    def test_exception(self):
        self.mock_cmds.GrowPolygonSelectionRegion.side_effect = RuntimeError("grow error")
        mod = _load_script("maya-selection", "grow_selection")
        result = mod.run({})
        assert result["success"] is False

    def test_prompt_present(self):
        mod = _load_script("maya-selection", "grow_selection")
        result = mod.run({})
        assert result["prompt"] is not None


class TestSelectionShrink:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.ls.side_effect = [
            ["pSphere1.f[0]", "pSphere1.f[1]", "pSphere1.f[2]"],  # before
            ["pSphere1.f[1]"],  # after
        ]

    def teardown_method(self):
        _cleanup_maya()

    def test_shrink_success(self):
        mod = _load_script("maya-selection", "shrink_selection")
        result = mod.run({})
        assert result["success"] is True
        assert result["context"]["removed"] == 2

    def test_shrink_calls_command(self):
        mod = _load_script("maya-selection", "shrink_selection")
        mod.run({})
        self.mock_cmds.ShrinkPolygonSelectionRegion.assert_called_once()

    def test_exception(self):
        self.mock_cmds.ShrinkPolygonSelectionRegion.side_effect = RuntimeError("shrink error")
        mod = _load_script("maya-selection", "shrink_selection")
        result = mod.run({})
        assert result["success"] is False

    def test_prompt_present(self):
        mod = _load_script("maya-selection", "shrink_selection")
        result = mod.run({})
        assert result["prompt"] is not None


class TestSelectionInvert:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.ls.side_effect = [
            ["pSphere1", "pCube1"],  # before
            ["pCylinder1", "pPlane1"],  # after
        ]

    def teardown_method(self):
        _cleanup_maya()

    def test_invert_success(self):
        mod = _load_script("maya-selection", "invert_selection")
        result = mod.run({})
        assert result["success"] is True
        assert result["context"]["before_count"] == 2
        assert result["context"]["after_count"] == 2

    def test_invert_calls_command(self):
        mod = _load_script("maya-selection", "invert_selection")
        mod.run({})
        self.mock_cmds.InvertSelection.assert_called_once()

    def test_exception(self):
        self.mock_cmds.InvertSelection.side_effect = RuntimeError("invert error")
        mod = _load_script("maya-selection", "invert_selection")
        result = mod.run({})
        assert result["success"] is False


class TestSelectionConvert:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.ls.return_value = ["pSphere1"]
        self.mock_cmds.polyListComponentConversion.return_value = [
            "pSphere1.vtx[0]",
            "pSphere1.vtx[1]",
        ]

    def teardown_method(self):
        _cleanup_maya()

    def test_convert_to_vertex(self):
        mod = _load_script("maya-selection", "convert_selection")
        result = mod.run({"target": "vertex"})
        assert result["success"] is True
        assert result["context"]["target"] == "vertex"

    def test_convert_to_edge(self):
        mod = _load_script("maya-selection", "convert_selection")
        result = mod.run({"target": "edge"})
        assert result["success"] is True

    def test_invalid_target(self):
        mod = _load_script("maya-selection", "convert_selection")
        result = mod.run({"target": "blob"})
        assert result["success"] is False

    def test_empty_selection(self):
        self.mock_cmds.ls.return_value = []
        mod = _load_script("maya-selection", "convert_selection")
        result = mod.run({"target": "face"})
        assert result["success"] is False

    def test_exception(self):
        self.mock_cmds.polyListComponentConversion.side_effect = RuntimeError("conv error")
        mod = _load_script("maya-selection", "convert_selection")
        result = mod.run({"target": "edge"})
        assert result["success"] is False


class TestSelectionSelectSimilar:
    def setup_method(self):
        self.mock_cmds = _make_mock_maya()
        self.mock_cmds.ls.return_value = ["pSphere1", "pSphere2"]
        self.mock_cmds.listRelatives.return_value = ["pSphereShape1"]
        self.mock_cmds.objectType.return_value = "mesh"
        self.mock_cmds.polyEvaluate.return_value = 382

    def teardown_method(self):
        _cleanup_maya()

    def test_select_by_type(self):
        # Reset ls to return selection then all-objects list
        self.mock_cmds.ls.side_effect = [
            ["pSphere1"],  # selection=True first call
            ["pSphere1", "pSphere2", "pCube1"],  # all objects ls()
        ]
        self.mock_cmds.objectType.return_value = "transform"
        mod = _load_script("maya-selection", "select_similar")
        result = mod.run({"criteria": "type"})
        assert result["success"] is True

    def test_nothing_selected(self):
        self.mock_cmds.ls.return_value = []
        mod = _load_script("maya-selection", "select_similar")
        result = mod.run({"criteria": "topology"})
        assert result["success"] is False

    def test_invalid_criteria(self):
        mod = _load_script("maya-selection", "select_similar")
        result = mod.run({"criteria": "invalid"})
        assert result["success"] is False

    def test_name_prefix(self):
        self.mock_cmds.ls.side_effect = [
            ["pSphere1"],  # selection
            ["pSphere1", "pSphere2", "pCube1"],  # cmds.ls() for all
        ]
        mod = _load_script("maya-selection", "select_similar")
        result = mod.run({"criteria": "name_prefix", "prefix": "pSphere"})
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exception(self):
        self.mock_cmds.ls.side_effect = [["pSphere1"], RuntimeError("ls error")]
        mod = _load_script("maya-selection", "select_similar")
        result = mod.run({"criteria": "type"})
        assert result["success"] is False
