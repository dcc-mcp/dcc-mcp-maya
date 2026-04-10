"""Round 14: Unit tests for maya-arnold-aov and maya-bifrost Skill domains.

All tests use importlib.util to load scripts from hyphenated directories and
mock maya.cmds / Arnold / Bifrost APIs.
"""

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Load a skill script module by path."""
    script_path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "{}.{}".format(skill_dir.replace("-", "_"), script_name),
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_mock_maya(cmds_attrs=None):
    """Return (mock_maya, mock_cmds) with the .cmds linkage wired correctly."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mock_cmds, k, v)
    return mock_maya, mock_cmds


# ---------------------------------------------------------------------------
# maya-arnold-aov
# ---------------------------------------------------------------------------


class TestAddAov:
    """Tests for maya-arnold-aov/scripts/add_aov.py."""

    def test_add_aov_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []
        mock_cmds.createNode.return_value = "aiAOV_diffuse"
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.return_value = []  # multiIndices

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "add_aov")
            result = mod.add_aov("diffuse")

        assert result["success"] is True
        assert "diffuse" in result["message"]
        assert result["context"]["aov_node"] == "aiAOV_diffuse"

    def test_add_aov_infers_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []
        mock_cmds.createNode.return_value = "aiAOV_Z"
        mock_cmds.objExists.return_value = False
        mock_cmds.getAttr.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "add_aov")
            result = mod.add_aov("Z")

        assert result["success"] is True
        assert result["context"]["aov_type"] == "FLOAT"

    def test_add_aov_custom_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []
        mock_cmds.createNode.return_value = "aiAOV_mypass"
        mock_cmds.objExists.return_value = False
        mock_cmds.getAttr.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "add_aov")
            result = mod.add_aov("mypass", aov_type="VECTOR")

        assert result["success"] is True
        assert result["context"]["aov_type"] == "VECTOR"

    def test_add_aov_empty_name(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "add_aov")
            result = mod.add_aov("")

        assert result["success"] is False
        assert "required" in result["message"].lower()

    def test_add_aov_already_exists(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_diffuse"]
        mock_cmds.getAttr.return_value = "diffuse"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "add_aov")
            result = mod.add_aov("diffuse")

        assert result["success"] is False
        assert "already exists" in result["message"]

    def test_add_aov_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("Arnold unavailable")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "add_aov")
            result = mod.add_aov("diffuse")

        assert result["success"] is False

    def test_add_aov_prompt_present(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []
        mock_cmds.createNode.return_value = "aiAOV_specular"
        mock_cmds.objExists.return_value = False
        mock_cmds.getAttr.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "add_aov")
            result = mod.add_aov("specular")

        assert result.get("prompt"), "prompt should be present"


class TestListAovs:
    """Tests for maya-arnold-aov/scripts/list_aovs.py."""

    def test_list_aovs_empty(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "list_aovs")
            result = mod.list_aovs()

        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["aovs"] == []

    def test_list_aovs_with_nodes(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_diffuse", "aiAOV_Z"]

        def getattr_side(attr):
            if "name" in attr:
                return attr.split("_")[1].split(".")[0]
            if "type" in attr:
                return 3
            if "enabled" in attr:
                return 1
            return None

        mock_cmds.getAttr.side_effect = getattr_side

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "list_aovs")
            result = mod.list_aovs()

        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_list_aovs_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "list_aovs")
            result = mod.list_aovs()

        assert result["success"] is False

    def test_list_aovs_prompt_present(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "list_aovs")
            result = mod.list_aovs()

        assert result.get("prompt"), "prompt should be present"


class TestDeleteAov:
    """Tests for maya-arnold-aov/scripts/delete_aov.py."""

    def test_delete_aov_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_diffuse"]
        mock_cmds.getAttr.return_value = "diffuse"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "delete_aov")
            result = mod.delete_aov("diffuse")

        assert result["success"] is True
        mock_cmds.delete.assert_called_once_with("aiAOV_diffuse")

    def test_delete_aov_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "delete_aov")
            result = mod.delete_aov("specular")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_delete_aov_empty_name(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "delete_aov")
            result = mod.delete_aov("")

        assert result["success"] is False

    def test_delete_aov_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "delete_aov")
            result = mod.delete_aov("diffuse")

        assert result["success"] is False

    def test_delete_aov_prompt_present(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_diffuse"]
        mock_cmds.getAttr.return_value = "diffuse"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "delete_aov")
            result = mod.delete_aov("diffuse")

        assert result.get("prompt"), "prompt should be present"


class TestSetAovAttribute:
    """Tests for maya-arnold-aov/scripts/set_aov_attribute.py."""

    def test_set_aov_attribute_bool(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_diffuse"]
        mock_cmds.getAttr.return_value = "diffuse"
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "set_aov_attribute")
            result = mod.set_aov_attribute("diffuse", "enabled", False)

        assert result["success"] is True
        assert result["context"]["value"] is False

    def test_set_aov_attribute_string(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_Z"]
        mock_cmds.getAttr.return_value = "Z"
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "set_aov_attribute")
            result = mod.set_aov_attribute("Z", "name", "depth")

        assert result["success"] is True
        mock_cmds.setAttr.assert_called_once()

    def test_set_aov_attribute_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "set_aov_attribute")
            result = mod.set_aov_attribute("missing", "enabled", True)

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_set_aov_attribute_missing_attr(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_diffuse"]

        def getattr_side(attr, **kw):
            if "name" in attr:
                return "diffuse"
            raise RuntimeError("no attr")

        mock_cmds.getAttr.side_effect = getattr_side
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "set_aov_attribute")
            result = mod.set_aov_attribute("diffuse", "badAttr", 1)

        assert result["success"] is False

    def test_set_aov_attribute_empty_name(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "set_aov_attribute")
            result = mod.set_aov_attribute("", "enabled", True)

        assert result["success"] is False

    def test_set_aov_attribute_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "set_aov_attribute")
            result = mod.set_aov_attribute("diffuse", "enabled", True)

        assert result["success"] is False


class TestEnableAov:
    """Tests for maya-arnold-aov/scripts/enable_aov.py."""

    def test_enable_aov_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_diffuse"]
        mock_cmds.getAttr.return_value = "diffuse"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "enable_aov")
            result = mod.enable_aov("diffuse", True)

        assert result["success"] is True
        assert result["context"]["enabled"] is True
        mock_cmds.setAttr.assert_called()

    def test_disable_aov(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["aiAOV_specular"]
        mock_cmds.getAttr.return_value = "specular"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "enable_aov")
            result = mod.enable_aov("specular", False)

        assert result["success"] is True
        assert result["context"]["enabled"] is False

    def test_enable_aov_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "enable_aov")
            result = mod.enable_aov("missing", True)

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_enable_aov_empty_name(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "enable_aov")
            result = mod.enable_aov("")

        assert result["success"] is False

    def test_enable_aov_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-arnold-aov", "enable_aov")
            result = mod.enable_aov("diffuse")

        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-bifrost
# ---------------------------------------------------------------------------


class TestCreateBifrostGraph:
    """Tests for maya-bifrost/scripts/create_bifrost_graph.py."""

    def test_create_bifrost_graph_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.createNode.return_value = "bifrostGraph1"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "create_bifrost_graph")
            result = mod.create_bifrost_graph()

        assert result["success"] is True
        assert result["context"]["graph_node"] == "bifrostGraph1"

    def test_create_bifrost_graph_with_name(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.createNode.return_value = "myGraph"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "create_bifrost_graph")
            result = mod.create_bifrost_graph("myGraph")

        assert result["success"] is True
        mock_cmds.createNode.assert_called_once_with("bifrostGraph", name="myGraph")

    def test_create_bifrost_graph_loads_plugin(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.pluginInfo.return_value = False
        mock_cmds.createNode.return_value = "bifrostGraph1"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "create_bifrost_graph")
            result = mod.create_bifrost_graph()

        mock_cmds.loadPlugin.assert_called_once_with("bifrostGraph")
        assert result["success"] is True

    def test_create_bifrost_graph_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.pluginInfo.side_effect = RuntimeError("fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "create_bifrost_graph")
            result = mod.create_bifrost_graph()

        assert result["success"] is False

    def test_create_bifrost_graph_prompt_present(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.createNode.return_value = "bifrostGraph1"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "create_bifrost_graph")
            result = mod.create_bifrost_graph()

        assert result.get("prompt"), "prompt should be present"


class TestListBifrostGraphs:
    """Tests for maya-bifrost/scripts/list_bifrost_graphs.py."""

    def test_list_bifrost_graphs_empty(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "list_bifrost_graphs")
            result = mod.list_bifrost_graphs()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_bifrost_graphs_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["bifrostGraph1", "bifrostGraph2"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "list_bifrost_graphs")
            result = mod.list_bifrost_graphs()

        assert result["success"] is True
        assert result["context"]["count"] == 2
        assert "bifrostGraph1" in result["context"]["graphs"]

    def test_list_bifrost_graphs_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "list_bifrost_graphs")
            result = mod.list_bifrost_graphs()

        assert result["success"] is False

    def test_list_bifrost_graphs_prompt_present(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "list_bifrost_graphs")
            result = mod.list_bifrost_graphs()

        assert result.get("prompt"), "prompt should be present"


class TestAddBifrostNode:
    """Tests for maya-bifrost/scripts/add_bifrost_node.py."""

    def test_add_bifrost_node_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "bifrostGraph"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "add_bifrost_node")
            result = mod.add_bifrost_node("bifrostGraph1", "Bifrost::Object::get_property")

        assert result["success"] is True
        mock_cmds.vnnCompound.assert_called_once()

    def test_add_bifrost_node_empty_graph(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "add_bifrost_node")
            result = mod.add_bifrost_node("", "Bifrost::Object::get_property")

        assert result["success"] is False

    def test_add_bifrost_node_empty_compound(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "add_bifrost_node")
            result = mod.add_bifrost_node("bifrostGraph1", "")

        assert result["success"] is False

    def test_add_bifrost_node_graph_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "add_bifrost_node")
            result = mod.add_bifrost_node("missingGraph", "compound")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_add_bifrost_node_wrong_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "add_bifrost_node")
            result = mod.add_bifrost_node("pCube1", "compound")

        assert result["success"] is False
        assert "not a bifrostGraph" in result["message"]

    def test_add_bifrost_node_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.side_effect = RuntimeError("fail")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "add_bifrost_node")
            result = mod.add_bifrost_node("bifrostGraph1", "compound")

        assert result["success"] is False


class TestConnectBifrostPorts:
    """Tests for maya-bifrost/scripts/connect_bifrost_ports.py."""

    def test_connect_ports_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "connect_bifrost_ports")
            result = mod.connect_bifrost_ports(
                "bifrostGraph1",
                "/get_property",
                "value",
                "/set_property",
                "value",
            )

        assert result["success"] is True
        mock_cmds.vnnConnect.assert_called_once()

    def test_connect_ports_empty_graph(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "connect_bifrost_ports")
            result = mod.connect_bifrost_ports("", "/src", "out", "/dst", "in")

        assert result["success"] is False

    def test_connect_ports_graph_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "connect_bifrost_ports")
            result = mod.connect_bifrost_ports("missing", "/src", "out", "/dst", "in")

        assert result["success"] is False

    def test_connect_ports_missing_port(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "connect_bifrost_ports")
            result = mod.connect_bifrost_ports("bifrostGraph1", "/src", "", "/dst", "in")

        assert result["success"] is False

    def test_connect_ports_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.vnnConnect.side_effect = RuntimeError("port error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "connect_bifrost_ports")
            result = mod.connect_bifrost_ports(
                "bifrostGraph1", "/src", "out", "/dst", "in"
            )

        assert result["success"] is False


class TestSetBifrostProperty:
    """Tests for maya-bifrost/scripts/set_bifrost_property.py."""

    def test_set_bifrost_property_int(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "set_bifrost_property")
            result = mod.set_bifrost_property("bifrostGraph1", "/scatter", "point_count", 1000)

        assert result["success"] is True
        assert result["context"]["value"] == 1000
        mock_cmds.vnnNode.assert_called_once()

    def test_set_bifrost_property_list(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "set_bifrost_property")
            result = mod.set_bifrost_property("bifrostGraph1", "/node", "offset", [1, 2, 3])

        assert result["success"] is True

    def test_set_bifrost_property_empty_graph(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "set_bifrost_property")
            result = mod.set_bifrost_property("", "/node", "port", 1)

        assert result["success"] is False

    def test_set_bifrost_property_graph_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "set_bifrost_property")
            result = mod.set_bifrost_property("missing", "/node", "port", 1)

        assert result["success"] is False

    def test_set_bifrost_property_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.vnnNode.side_effect = RuntimeError("vnn error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "set_bifrost_property")
            result = mod.set_bifrost_property("bifrostGraph1", "/node", "port", 42)

        assert result["success"] is False

    def test_set_bifrost_property_prompt_present(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-bifrost", "set_bifrost_property")
            result = mod.set_bifrost_property("bifrostGraph1", "/node", "port", 1)

        assert result.get("prompt"), "prompt should be present"
