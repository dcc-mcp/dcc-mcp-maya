"""Round 34: Deep edge-case tests for maya-arnold-aov and maya-bifrost skills.

Coverage targets:
- maya-arnold-aov: AOV type inference, duplicate check, defaultArnoldRenderOptions
  present/absent, disable flag, list with mixed getAttr failures, set_aov_attribute
  string vs numeric value, delete non-existent.
- maya-bifrost: plugin load/already-loaded paths, wrong node type guard,
  missing-param validation for all 5 scripts, list empty, set_bifrost_property
  list value serialisation.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock, call, patch

# Import third-party modules
import pytest

from conftest import SKILLS_ROOT, load_and_call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cmds(**overrides):
    """Return a MagicMock that looks like maya.cmds."""
    cmds = MagicMock()
    for k, v in overrides.items():
        setattr(cmds, k, v)
    return cmds


# ===========================================================================
# TestArnoldAovAddAov
# ===========================================================================


class TestArnoldAovAddAov:
    """Tests for maya-arnold-aov/scripts/add_aov.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-arnold-aov/scripts/add_aov.py", mock_cmds, **kwargs)

    def test_empty_name_returns_error(self):
        cmds = _make_cmds()
        result = self._call(cmds, name="")
        assert result["success"] is False
        assert "name" in result["message"].lower()

    def test_known_aov_type_inferred(self):
        """AOV type is inferred from _STANDARD_AOV_TYPES when aov_type is None."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_diffuse1"
        cmds.objExists.return_value = False

        result = self._call(cmds, name="diffuse")
        assert result["success"] is True
        assert result["context"]["aov_type"] == "RGB"

    def test_z_pass_inferred_as_float(self):
        """'Z' AOV should be inferred as FLOAT."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_Z1"
        cmds.objExists.return_value = False

        result = self._call(cmds, name="Z")
        assert result["success"] is True
        assert result["context"]["aov_type"] == "FLOAT"

    def test_custom_aov_type_explicit(self):
        """Explicit aov_type overrides inference."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_custom1"
        cmds.objExists.return_value = False

        result = self._call(cmds, name="my_custom", aov_type="VECTOR")
        assert result["success"] is True
        assert result["context"]["aov_type"] == "VECTOR"

    def test_unknown_aov_falls_back_to_rgb(self):
        """Unknown AOV names fall back to 'RGB'."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_unknown1"
        cmds.objExists.return_value = False

        result = self._call(cmds, name="my_unknown_pass")
        assert result["success"] is True
        assert result["context"]["aov_type"] == "RGB"

    def test_duplicate_aov_returns_error(self):
        """Adding AOV with already-existing name returns error."""
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"

        result = self._call(cmds, name="diffuse")
        assert result["success"] is False
        assert "already exists" in result["message"]

    def test_with_arnold_options_connects(self):
        """When defaultArnoldRenderOptions exists, connectAttr is called."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_beauty1"
        cmds.objExists.return_value = True  # defaultArnoldRenderOptions exists
        cmds.getAttr.return_value = []  # multiIndices returns empty → index 0

        result = self._call(cmds, name="beauty")
        assert result["success"] is True
        cmds.connectAttr.assert_called_once()

    def test_without_arnold_options_no_connect(self):
        """When defaultArnoldRenderOptions is absent, connectAttr is NOT called."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_diffuse1"
        cmds.objExists.return_value = False  # no defaultArnoldRenderOptions

        result = self._call(cmds, name="diffuse")
        assert result["success"] is True
        cmds.connectAttr.assert_not_called()

    def test_disabled_aov(self):
        """enabled=False is forwarded to the node attribute."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_Z1"
        cmds.objExists.return_value = False

        result = self._call(cmds, name="Z", enabled=False)
        assert result["success"] is True
        assert result["context"]["enabled"] is False

    def test_arnold_options_next_index_uses_existing_max(self):
        """Index = max(existing) + 1 when aovList already has entries."""
        cmds = _make_cmds()
        cmds.ls.return_value = []
        cmds.createNode.return_value = "aiAOV_specular1"
        cmds.objExists.return_value = True
        cmds.getAttr.return_value = [0, 2, 5]  # existing indices

        result = self._call(cmds, name="specular")
        assert result["success"] is True
        # connectAttr called with index 6
        connect_call_args = cmds.connectAttr.call_args
        assert "aovList[6]" in connect_call_args[0][1]


# ===========================================================================
# TestArnoldAovEnableAov
# ===========================================================================


class TestArnoldAovEnableAov:
    """Tests for maya-arnold-aov/scripts/enable_aov.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-arnold-aov/scripts/enable_aov.py", mock_cmds, **kwargs)

    def test_empty_name_returns_error(self):
        cmds = _make_cmds()
        result = self._call(cmds, name="")
        assert result["success"] is False

    def test_aov_not_found(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"

        result = self._call(cmds, name="specular")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_enable_happy_path(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"

        result = self._call(cmds, name="diffuse", enabled=True)
        assert result["success"] is True
        assert result["context"]["enabled"] is True
        cmds.setAttr.assert_called_once_with("aiAOV_diffuse1.enabled", True)

    def test_disable_happy_path(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"

        result = self._call(cmds, name="diffuse", enabled=False)
        assert result["success"] is True
        assert "disabled" in result["message"]

    def test_getattr_exception_skips_node(self):
        """If getAttr raises for one node, it is skipped and search continues."""
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_bad1", "aiAOV_good1"]

        # First getAttr raises, second returns "good"
        cmds.getAttr.side_effect = [Exception("bad node"), "good"]

        result = self._call(cmds, name="good", enabled=True)
        assert result["success"] is True
        assert result["context"]["aov_node"] == "aiAOV_good1"

    def test_no_aovs_in_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []

        result = self._call(cmds, name="beauty")
        assert result["success"] is False
        assert "not found" in result["message"]


# ===========================================================================
# TestArnoldAovListAovs
# ===========================================================================


class TestArnoldAovListAovs:
    """Tests for maya-arnold-aov/scripts/list_aovs.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-arnold-aov/scripts/list_aovs.py", mock_cmds, **kwargs)

    def test_empty_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []

        result = self._call(cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["aovs"] == []

    def test_two_aovs(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_beauty1", "aiAOV_Z1"]
        # getAttr returns for name, type_int, enabled per node
        cmds.getAttr.side_effect = ["beauty", 4, True, "Z", 1, True]

        result = self._call(cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 2
        aovs = result["context"]["aovs"]
        assert aovs[0]["name"] == "beauty"
        assert aovs[0]["type"] == "RGBA"
        assert aovs[1]["name"] == "Z"
        assert aovs[1]["type"] == "FLOAT"

    def test_getattr_exception_skips_bad_node(self):
        """Nodes where getAttr fails are silently skipped."""
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_bad1", "aiAOV_diffuse1"]
        cmds.getAttr.side_effect = [Exception("corrupt"), "diffuse", 3, True]

        result = self._call(cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["aovs"][0]["name"] == "diffuse"

    def test_unknown_type_int_falls_back_to_rgb(self):
        """An unknown type integer falls back to 'RGB'."""
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_custom1"]
        cmds.getAttr.side_effect = ["custom", 99, True]

        result = self._call(cmds)
        assert result["context"]["aovs"][0]["type"] == "RGB"

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = self._call(cmds)
        assert result.get("prompt")


# ===========================================================================
# TestArnoldAovDeleteAov
# ===========================================================================


class TestArnoldAovDeleteAov:
    """Tests for maya-arnold-aov/scripts/delete_aov.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-arnold-aov/scripts/delete_aov.py", mock_cmds, **kwargs)

    def test_empty_name(self):
        cmds = _make_cmds()
        result = self._call(cmds, name="")
        assert result["success"] is False

    def test_not_found(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = self._call(cmds, name="diffuse")
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_delete_found_node(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"

        result = self._call(cmds, name="diffuse")
        assert result["success"] is True
        cmds.delete.assert_called_once_with("aiAOV_diffuse1")
        assert result["context"]["deleted_node"] == "aiAOV_diffuse1"

    def test_getattr_exception_skips_and_not_found(self):
        """If getAttr raises for the only node, result is 'not found'."""
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_bad1"]
        cmds.getAttr.side_effect = Exception("bad")

        result = self._call(cmds, name="diffuse")
        assert result["success"] is False


# ===========================================================================
# TestArnoldAovSetAovAttribute
# ===========================================================================


class TestArnoldAovSetAovAttribute:
    """Tests for maya-arnold-aov/scripts/set_aov_attribute.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-arnold-aov/scripts/set_aov_attribute.py", mock_cmds, **kwargs)

    def test_empty_name(self):
        cmds = _make_cmds()
        result = self._call(cmds, name="", attribute="enabled", value=True)
        assert result["success"] is False

    def test_empty_attribute(self):
        cmds = _make_cmds()
        result = self._call(cmds, name="diffuse", attribute="", value=True)
        assert result["success"] is False

    def test_aov_not_found(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = self._call(cmds, name="diffuse", attribute="enabled", value=True)
        assert result["success"] is False
        assert "not found" in result["message"]

    def test_set_bool_value(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"
        cmds.objExists.return_value = True  # attr path exists

        result = self._call(cmds, name="diffuse", attribute="enabled", value=True)
        assert result["success"] is True
        # bool → setAttr without type="string"
        cmds.setAttr.assert_called_once_with("aiAOV_diffuse1.enabled", True)

    def test_set_string_value(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"
        cmds.objExists.return_value = True

        result = self._call(cmds, name="diffuse", attribute="name", value="my_diffuse")
        assert result["success"] is True
        cmds.setAttr.assert_called_once_with("aiAOV_diffuse1.name", "my_diffuse", type="string")

    def test_attr_not_exist_returns_error(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["aiAOV_diffuse1"]
        cmds.getAttr.return_value = "diffuse"
        cmds.objExists.return_value = False  # attr path does not exist

        result = self._call(cmds, name="diffuse", attribute="nonexistent", value=1)
        assert result["success"] is False


# ===========================================================================
# TestBifrostCreateGraph
# ===========================================================================


class TestBifrostCreateGraph:
    """Tests for maya-bifrost/scripts/create_bifrost_graph.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-bifrost/scripts/create_bifrost_graph.py", mock_cmds, **kwargs)

    def test_plugin_already_loaded(self):
        """When plugin is already loaded, loadPlugin should NOT be called."""
        cmds = _make_cmds()
        cmds.pluginInfo.return_value = True
        cmds.createNode.return_value = "bifrostGraph1"

        result = self._call(cmds)
        assert result["success"] is True
        cmds.loadPlugin.assert_not_called()

    def test_plugin_not_loaded_triggers_load(self):
        """When plugin is not loaded, loadPlugin should be called."""
        cmds = _make_cmds()
        cmds.pluginInfo.return_value = False
        cmds.createNode.return_value = "bifrostGraph1"

        result = self._call(cmds)
        assert result["success"] is True
        cmds.loadPlugin.assert_called_once_with("bifrostGraph")

    def test_with_name(self):
        cmds = _make_cmds()
        cmds.pluginInfo.return_value = True
        cmds.createNode.return_value = "myGraph"

        result = self._call(cmds, name="myGraph")
        assert result["success"] is True
        assert result["context"]["graph_node"] == "myGraph"
        # name kwarg forwarded to createNode
        cmds.createNode.assert_called_once_with("bifrostGraph", name="myGraph")

    def test_without_name(self):
        """No name → createNode called without name kwarg."""
        cmds = _make_cmds()
        cmds.pluginInfo.return_value = True
        cmds.createNode.return_value = "bifrostGraph1"

        result = self._call(cmds)
        assert result["success"] is True
        cmds.createNode.assert_called_once_with("bifrostGraph")

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.pluginInfo.return_value = True
        cmds.createNode.return_value = "bifrostGraph1"
        result = self._call(cmds)
        assert result.get("prompt")


# ===========================================================================
# TestBifrostAddNode
# ===========================================================================


class TestBifrostAddNode:
    """Tests for maya-bifrost/scripts/add_bifrost_node.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-bifrost/scripts/add_bifrost_node.py", mock_cmds, **kwargs)

    def test_empty_graph_node(self):
        cmds = _make_cmds()
        result = self._call(cmds, graph_node="", compound_name="Bifrost::Object::get_property")
        assert result["success"] is False
        assert "graph_node" in result["message"]

    def test_empty_compound_name(self):
        cmds = _make_cmds()
        result = self._call(cmds, graph_node="bifrostGraph1", compound_name="")
        assert result["success"] is False
        assert "compound_name" in result["message"]

    def test_graph_node_not_found(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = self._call(cmds, graph_node="noSuchNode", compound_name="SomeCompound")
        assert result["success"] is False

    def test_wrong_node_type(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "transform"

        result = self._call(cmds, graph_node="myTransform", compound_name="SomeCompound")
        assert result["success"] is False
        assert "bifrostGraph" in result["message"]

    def test_happy_path(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "bifrostGraph"

        result = self._call(cmds, graph_node="bifrostGraph1", compound_name="Bifrost::Math::add")
        assert result["success"] is True
        cmds.vnnCompound.assert_called_once_with("bifrostGraph1", "/", addNode="Bifrost::Math::add")

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "bifrostGraph"
        result = self._call(cmds, graph_node="bifrostGraph1", compound_name="Test::Compound")
        assert result.get("prompt")


# ===========================================================================
# TestBifrostConnectPorts
# ===========================================================================


class TestBifrostConnectPorts:
    """Tests for maya-bifrost/scripts/connect_bifrost_ports.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-bifrost/scripts/connect_bifrost_ports.py", mock_cmds, **kwargs)

    @pytest.mark.parametrize("missing_arg", [
        "graph_node", "source_node_path", "source_port", "target_node_path", "target_port"
    ])
    def test_missing_required_arg(self, missing_arg):
        """Each required argument missing should produce an error."""
        cmds = _make_cmds()
        full_kwargs = {
            "graph_node": "bifrostGraph1",
            "source_node_path": "/nodeA",
            "source_port": "out_value",
            "target_node_path": "/nodeB",
            "target_port": "in_value",
        }
        full_kwargs[missing_arg] = ""
        result = self._call(cmds, **full_kwargs)
        assert result["success"] is False
        assert missing_arg in result["message"]

    def test_graph_node_not_found(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = self._call(
            cmds,
            graph_node="noGraph",
            source_node_path="/A",
            source_port="out",
            target_node_path="/B",
            target_port="in",
        )
        assert result["success"] is False

    def test_happy_path(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True

        result = self._call(
            cmds,
            graph_node="bifrostGraph1",
            source_node_path="/scatter",
            source_port="out_points",
            target_node_path="/render",
            target_port="in_points",
        )
        assert result["success"] is True
        cmds.vnnConnect.assert_called_once_with(
            "bifrostGraph1",
            "/scatter.out_points",
            "/render.in_points",
        )

    def test_context_keys_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True

        result = self._call(
            cmds,
            graph_node="g1",
            source_node_path="/A",
            source_port="p1",
            target_node_path="/B",
            target_port="p2",
        )
        assert "source" in result["context"]
        assert "target" in result["context"]


# ===========================================================================
# TestBifrostListGraphs
# ===========================================================================


class TestBifrostListGraphs:
    """Tests for maya-bifrost/scripts/list_bifrost_graphs.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-bifrost/scripts/list_bifrost_graphs.py", mock_cmds, **kwargs)

    def test_empty_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []

        result = self._call(cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["graphs"] == []

    def test_two_graphs(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["bifrostGraph1", "bifrostGraph2"]

        result = self._call(cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 2
        assert "bifrostGraph1" in result["context"]["graphs"]

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = self._call(cmds)
        assert result.get("prompt")


# ===========================================================================
# TestBifrostSetProperty
# ===========================================================================


class TestBifrostSetProperty:
    """Tests for maya-bifrost/scripts/set_bifrost_property.py."""

    def _call(self, mock_cmds, **kwargs):
        return load_and_call("maya-bifrost/scripts/set_bifrost_property.py", mock_cmds, **kwargs)

    @pytest.mark.parametrize("missing_arg", ["graph_node", "node_path", "port_name"])
    def test_missing_required_arg(self, missing_arg):
        cmds = _make_cmds()
        full_kwargs = {
            "graph_node": "bifrostGraph1",
            "node_path": "/scatter",
            "port_name": "count",
            "value": 100,
        }
        full_kwargs[missing_arg] = ""
        result = self._call(cmds, **full_kwargs)
        assert result["success"] is False

    def test_graph_node_not_found(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = self._call(
            cmds,
            graph_node="noGraph",
            node_path="/A",
            port_name="count",
            value=1,
        )
        assert result["success"] is False

    def test_numeric_value(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True

        result = self._call(
            cmds,
            graph_node="bifrostGraph1",
            node_path="/scatter",
            port_name="point_count",
            value=500,
        )
        assert result["success"] is True
        cmds.vnnNode.assert_called_once_with(
            "bifrostGraph1",
            "/scatter",
            setPortDefaultValues=["point_count", "500"],
        )

    def test_string_value(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True

        result = self._call(
            cmds,
            graph_node="bifrostGraph1",
            node_path="/scatter",
            port_name="mode",
            value="random",
        )
        assert result["success"] is True
        cmds.vnnNode.assert_called_once_with(
            "bifrostGraph1",
            "/scatter",
            setPortDefaultValues=["mode", "random"],
        )

    def test_list_value_joined_as_string(self):
        """List values are space-joined for Bifrost vector format."""
        cmds = _make_cmds()
        cmds.objExists.return_value = True

        result = self._call(
            cmds,
            graph_node="bifrostGraph1",
            node_path="/transform",
            port_name="translate",
            value=[1.0, 2.0, 3.0],
        )
        assert result["success"] is True
        cmds.vnnNode.assert_called_once_with(
            "bifrostGraph1",
            "/transform",
            setPortDefaultValues=["translate", "1.0 2.0 3.0"],
        )

    def test_tuple_value_joined(self):
        """Tuple values are also space-joined."""
        cmds = _make_cmds()
        cmds.objExists.return_value = True

        result = self._call(
            cmds,
            graph_node="bifrostGraph1",
            node_path="/node",
            port_name="color",
            value=(0.5, 0.5, 0.5),
        )
        assert result["success"] is True
        call_args = cmds.vnnNode.call_args
        assert call_args[1]["setPortDefaultValues"][1] == "0.5 0.5 0.5"

    def test_context_keys_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True

        result = self._call(
            cmds,
            graph_node="bifrostGraph1",
            node_path="/node",
            port_name="val",
            value=42,
        )
        ctx = result["context"]
        assert "graph_node" in ctx
        assert "node_path" in ctx
        assert "port_name" in ctx
        assert "value" in ctx

    def test_prompt_present(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        result = self._call(
            cmds,
            graph_node="g1",
            node_path="/n",
            port_name="p",
            value=1,
        )
        assert result.get("prompt")
