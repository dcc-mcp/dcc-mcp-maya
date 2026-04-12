"""Round 43: Arnold mtoa plugin availability checks for maya-arnold-aov scripts.

Tests that all five maya-arnold-aov scripts correctly guard against a missing
mtoa plugin and return appropriate results when Arnold is and is not loaded.
"""

# Import built-in modules
import importlib
import sys
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mocks(mtoa_loaded: bool = True):
    """Return (mock_cmds, mock_maya) with pluginInfo pre-configured."""
    mock_cmds = MagicMock()
    mock_cmds.pluginInfo.return_value = mtoa_loaded  # covers loaded=True query
    mock_cmds.ls.return_value = []
    mock_cmds.createNode.return_value = "aiAOV_diffuse1"
    mock_cmds.getAttr.return_value = None
    mock_cmds.objExists.return_value = True
    mock_cmds.attributeQuery.return_value = True

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    return mock_cmds, mock_maya


def _load_and_call(script_relpath: str, func_name: str, mtoa_loaded: bool, **kwargs):
    """Load a skill script with patched Maya env and call func_name(**kwargs)."""
    mock_cmds, mock_maya = _make_mocks(mtoa_loaded=mtoa_loaded)

    mods = {
        "maya": mock_maya,
        "maya.cmds": mock_cmds,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }

    with patch.dict(sys.modules, mods):
        spec = importlib.util.spec_from_file_location("_test_mod", script_relpath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, func_name)
        return func(**kwargs), mock_cmds


# ---------------------------------------------------------------------------
# add_aov
# ---------------------------------------------------------------------------

_ADD_AOV = "src/dcc_mcp_maya/skills/maya-arnold-aov/scripts/add_aov.py"


class TestAddAovMtoaCheck:
    """add_aov — Arnold plugin guard."""

    def test_mtoa_not_loaded_returns_error(self):
        result, _ = _load_and_call(_ADD_AOV, "add_aov", mtoa_loaded=False, name="diffuse")
        assert result["success"] is False
        assert "mtoa" in result["message"].lower() or "arnold" in result["message"].lower()

    def test_mtoa_not_loaded_solution_mentions_load(self):
        result, _ = _load_and_call(_ADD_AOV, "add_aov", mtoa_loaded=False, name="diffuse")
        solution = result.get("context", {}).get("solution", "") or result.get("error", "")
        assert "loadPlugin" in solution or "mtoa" in solution.lower() or "mtoa" in result["message"].lower()

    def test_mtoa_loaded_proceeds_to_create_node(self):
        mock_cmds, _ = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = []
        mock_cmds.createNode.return_value = "aiAOV_diffuse1"

        mods = {
            "maya": MagicMock(cmds=mock_cmds),
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_add_aov", _ADD_AOV)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.add_aov(name="diffuse")

        assert result["success"] is True
        mock_cmds.createNode.assert_called_once()

    def test_empty_name_checked_before_plugin(self):
        """Empty name validation fires before plugin check."""
        result, _ = _load_and_call(_ADD_AOV, "add_aov", mtoa_loaded=False, name="")
        assert result["success"] is False
        assert "name" in result["message"].lower()

    def test_mtoa_loaded_success_has_aov_node(self):
        mock_cmds, _ = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = []
        mock_cmds.createNode.return_value = "aiAOV_diffuse1"
        mock_cmds.objExists.return_value = False

        mods = {
            "maya": MagicMock(cmds=mock_cmds),
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_add_aov2", _ADD_AOV)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.add_aov(name="diffuse")

        assert "aov_node" in result.get("context", {})


# ---------------------------------------------------------------------------
# list_aovs
# ---------------------------------------------------------------------------

_LIST_AOVS = "src/dcc_mcp_maya/skills/maya-arnold-aov/scripts/list_aovs.py"


class TestListAovsMtoaCheck:
    """list_aovs — graceful empty result when mtoa absent."""

    def test_mtoa_not_loaded_returns_success_empty(self):
        result, _ = _load_and_call(_LIST_AOVS, "list_aovs", mtoa_loaded=False)
        assert result["success"] is True
        assert result.get("context", {}).get("count", -1) == 0
        assert result.get("context", {}).get("aovs") == []

    def test_mtoa_not_loaded_message_mentions_arnold(self):
        result, _ = _load_and_call(_LIST_AOVS, "list_aovs", mtoa_loaded=False)
        assert "arnold" in result["message"].lower() or "mtoa" in result["message"].lower()

    def test_mtoa_not_loaded_has_helpful_prompt(self):
        result, _ = _load_and_call(_LIST_AOVS, "list_aovs", mtoa_loaded=False)
        # prompt is stored at top-level by skill_success helper
        prompt = result.get("prompt", "") or result.get("context", {}).get("prompt", "")
        assert prompt  # prompt should not be empty

    def test_mtoa_loaded_queries_ls_aiAOV(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = []

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_list_aovs", _LIST_AOVS)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.list_aovs()

        assert result["success"] is True
        mock_cmds.ls.assert_called()

    def test_mtoa_loaded_with_aovs_returns_list(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = ["aiAOV_diffuse1", "aiAOV_beauty1"]
        mock_cmds.getAttr.side_effect = lambda attr: (
            "diffuse" if "diffuse" in attr else ("beauty" if "beauty" in attr else 3)
        )

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_list_aovs2", _LIST_AOVS)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.list_aovs()

        assert result["success"] is True
        assert result["context"]["count"] == 2


# ---------------------------------------------------------------------------
# enable_aov
# ---------------------------------------------------------------------------

_ENABLE_AOV = "src/dcc_mcp_maya/skills/maya-arnold-aov/scripts/enable_aov.py"


class TestEnableAovMtoaCheck:
    """enable_aov — Arnold plugin guard."""

    def test_mtoa_not_loaded_returns_error(self):
        result, _ = _load_and_call(_ENABLE_AOV, "enable_aov", mtoa_loaded=False, name="diffuse")
        assert result["success"] is False
        assert "mtoa" in result["message"].lower() or "arnold" in result["message"].lower()

    def test_empty_name_checked_before_plugin(self):
        result, _ = _load_and_call(_ENABLE_AOV, "enable_aov", mtoa_loaded=False, name="")
        assert result["success"] is False
        assert "name" in result["message"].lower()

    def test_mtoa_loaded_aov_not_found(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = []

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_enable_aov", _ENABLE_AOV)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.enable_aov(name="diffuse")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_mtoa_loaded_enable_success(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = ["aiAOV_diffuse1"]
        mock_cmds.getAttr.return_value = "diffuse"

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_enable_aov2", _ENABLE_AOV)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.enable_aov(name="diffuse", enabled=True)

        assert result["success"] is True
        assert result["context"]["enabled"] is True


# ---------------------------------------------------------------------------
# delete_aov
# ---------------------------------------------------------------------------

_DELETE_AOV = "src/dcc_mcp_maya/skills/maya-arnold-aov/scripts/delete_aov.py"


class TestDeleteAovMtoaCheck:
    """delete_aov — Arnold plugin guard."""

    def test_mtoa_not_loaded_returns_error(self):
        result, _ = _load_and_call(_DELETE_AOV, "delete_aov", mtoa_loaded=False, name="diffuse")
        assert result["success"] is False
        assert "arnold" in result["message"].lower() or "mtoa" in result["message"].lower()

    def test_empty_name_checked_before_plugin(self):
        result, _ = _load_and_call(_DELETE_AOV, "delete_aov", mtoa_loaded=False, name="")
        assert result["success"] is False
        assert "name" in result["message"].lower()

    def test_mtoa_loaded_aov_not_found(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = []

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_delete_aov", _DELETE_AOV)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.delete_aov(name="diffuse")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_mtoa_loaded_delete_success(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = ["aiAOV_diffuse1"]
        mock_cmds.getAttr.return_value = "diffuse"

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_delete_aov2", _DELETE_AOV)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.delete_aov(name="diffuse")

        assert result["success"] is True
        mock_cmds.delete.assert_called_once_with("aiAOV_diffuse1")


# ---------------------------------------------------------------------------
# set_aov_attribute
# ---------------------------------------------------------------------------

_SET_AOV_ATTR = "src/dcc_mcp_maya/skills/maya-arnold-aov/scripts/set_aov_attribute.py"


class TestSetAovAttributeMtoaCheck:
    """set_aov_attribute — Arnold plugin guard."""

    def test_mtoa_not_loaded_returns_error(self):
        result, _ = _load_and_call(
            _SET_AOV_ATTR, "set_aov_attribute", mtoa_loaded=False, name="diffuse", attribute="type", value=3
        )
        assert result["success"] is False
        assert "arnold" in result["message"].lower() or "mtoa" in result["message"].lower()

    def test_empty_name_checked_before_plugin(self):
        result, _ = _load_and_call(
            _SET_AOV_ATTR, "set_aov_attribute", mtoa_loaded=False, name="", attribute="type", value=3
        )
        assert result["success"] is False
        assert "name" in result["message"].lower()

    def test_empty_attribute_checked_before_plugin(self):
        result, _ = _load_and_call(
            _SET_AOV_ATTR, "set_aov_attribute", mtoa_loaded=False, name="diffuse", attribute="", value=3
        )
        assert result["success"] is False
        assert "attribute" in result["message"].lower()

    def test_mtoa_loaded_aov_not_found(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = []

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_set_aov_attr", _SET_AOV_ATTR)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.set_aov_attribute(name="diffuse", attribute="type", value=3)

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_mtoa_loaded_set_success(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = ["aiAOV_diffuse1"]
        mock_cmds.getAttr.return_value = "diffuse"
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_set_aov_attr2", _SET_AOV_ATTR)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.set_aov_attribute(name="diffuse", attribute="enabled", value=False)

        assert result["success"] is True
        assert "aov_node" in result.get("context", {})

    def test_mtoa_loaded_string_value_uses_type_string(self):
        mock_cmds, mock_maya = _make_mocks(mtoa_loaded=True)
        mock_cmds.ls.return_value = ["aiAOV_diffuse1"]
        mock_cmds.getAttr.return_value = "diffuse"
        mock_cmds.objExists.return_value = True
        mock_cmds.attributeQuery.return_value = True

        mods = {
            "maya": mock_maya,
            "maya.cmds": mock_cmds,
            "maya.api": MagicMock(),
            "maya.utils": MagicMock(),
        }
        with patch.dict(sys.modules, mods):
            spec = importlib.util.spec_from_file_location("_set_aov_attr3", _SET_AOV_ATTR)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.set_aov_attribute(name="diffuse", attribute="name", value="custom_name")

        # setAttr called with type="string"
        calls = mock_cmds.setAttr.call_args_list
        string_calls = [c for c in calls if c.kwargs.get("type") == "string" or "string" in str(c)]
        assert string_calls


# ---------------------------------------------------------------------------
# Structural: pluginInfo call present in all 5 scripts
# ---------------------------------------------------------------------------

_AOV_SCRIPTS = [
    _ADD_AOV,
    _LIST_AOVS,
    _ENABLE_AOV,
    _DELETE_AOV,
    _SET_AOV_ATTR,
]


class TestAovScriptsStructural:
    """Verify pluginInfo guard is present in all 5 AOV scripts."""

    def test_all_scripts_have_plugin_info_check(self):
        for path in _AOV_SCRIPTS:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            assert "pluginInfo" in content, "Missing pluginInfo check in {}".format(path)

    def test_all_scripts_reference_mtoa(self):
        for path in _AOV_SCRIPTS:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            assert "mtoa" in content, "Missing 'mtoa' reference in {}".format(path)

    def test_add_aov_returns_error_when_no_mtoa(self):
        """Ensure add_aov uses skill_error (not skill_success) for mtoa absent."""
        with open(_ADD_AOV, encoding="utf-8") as fh:
            content = fh.read()
        # The error return must appear after pluginInfo check
        plugin_pos = content.find("pluginInfo")
        error_pos = content.find("skill_error", plugin_pos)
        assert error_pos != -1

    def test_list_aovs_returns_success_when_no_mtoa(self):
        """list_aovs uses skill_success (empty) so agent isn't blocked."""
        with open(_LIST_AOVS, encoding="utf-8") as fh:
            content = fh.read()
        plugin_pos = content.find("pluginInfo")
        # After pluginInfo check, there must be a skill_success call (graceful empty)
        success_pos = content.find("skill_success", plugin_pos)
        assert success_pos != -1
