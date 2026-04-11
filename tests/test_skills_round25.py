"""Round 25 tests — api.py new helpers + skinning-utils refactor integration.

New helpers tested:
- batch_validate_nodes: validates multiple nodes in one call
- require_any_param: returns first found key from params
- get_param_list: normalises str/list/None → list

Skinning-utils integration:
- copy_skin_weights now uses batch_validate_nodes
- normalize_skin_weights, mirror_skin_weights, prune_skin_weights use validate_node_exists
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import os
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_maya():
    """Return (mock_maya_pkg, mock_cmds) with sane defaults."""
    mock_maya = MagicMock()
    mock_cmds = MagicMock()
    mock_cmds.objExists.return_value = True
    mock_cmds.objectType.return_value = "transform"
    mock_maya.cmds = mock_cmds
    return mock_maya, mock_cmds


SKILLS_BASE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "dcc_mcp_maya",
    "skills",
)


def _load_script(skill_dir: str, script_name: str):
    """Dynamically load a skill script module, bypassing the Maya import guard."""
    path = os.path.normpath(os.path.join(SKILLS_BASE, skill_dir, "scripts", script_name + ".py"))
    spec = importlib.util.spec_from_file_location(script_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# TestBatchValidateNodes
# ---------------------------------------------------------------------------


class TestBatchValidateNodes:
    """Tests for dcc_mcp_maya.api.batch_validate_nodes."""

    def _get_helper(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        return batch_validate_nodes

    def test_all_exist_returns_none(self):
        batch_validate_nodes = self._get_helper()
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = True
        result = batch_validate_nodes(cmds_mock, ["a", "b", "c"])
        assert result is None

    def test_empty_list_returns_none(self):
        batch_validate_nodes = self._get_helper()
        cmds_mock = MagicMock()
        result = batch_validate_nodes(cmds_mock, [])
        assert result is None

    def test_first_missing_returns_error(self):
        batch_validate_nodes = self._get_helper()
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = False
        result = batch_validate_nodes(cmds_mock, ["missingNode", "otherNode"])
        assert result is not None
        assert result["success"] is False
        assert "missingNode" in result["message"]

    def test_second_missing_returns_error(self):
        batch_validate_nodes = self._get_helper()
        cmds_mock = MagicMock()

        def exists_side(name):
            return name == "existingNode"

        cmds_mock.objExists.side_effect = exists_side
        result = batch_validate_nodes(cmds_mock, ["existingNode", "missingSecond"])
        assert result is not None
        assert result["success"] is False
        assert "missingSecond" in result["message"]

    def test_stops_at_first_missing(self):
        """batch_validate_nodes should short-circuit on first failure."""
        batch_validate_nodes = self._get_helper()
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = False
        result = batch_validate_nodes(cmds_mock, ["a", "b", "c"])
        assert "a" in result["message"]
        # objExists should have been called only once (short-circuit)
        assert cmds_mock.objExists.call_count == 1

    def test_possible_solutions_present(self):
        batch_validate_nodes = self._get_helper()
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = False
        result = batch_validate_nodes(cmds_mock, ["ghost"])
        assert "possible_solutions" in result.get("context", {}) or "possible_solutions" in result

    def test_reexported_from_package(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "batch_validate_nodes")


# ---------------------------------------------------------------------------
# TestRequireAnyParam
# ---------------------------------------------------------------------------


class TestRequireAnyParam:
    """Tests for dcc_mcp_maya.api.require_any_param."""

    def _get_helper(self):
        from dcc_mcp_maya.api import require_any_param

        return require_any_param

    def test_first_key_found(self):
        require_any_param = self._get_helper()
        assert require_any_param({"name": "foo"}, "name", "node_name") == "foo"

    def test_second_key_found(self):
        require_any_param = self._get_helper()
        assert require_any_param({"node_name": "bar"}, "name", "node_name") == "bar"

    def test_last_key_found(self):
        require_any_param = self._get_helper()
        assert require_any_param({"object": "baz"}, "name", "node_name", "object") == "baz"

    def test_none_found_raises(self):
        from dcc_mcp_maya.api import MissingParamError, require_any_param

        with pytest.raises(MissingParamError):
            require_any_param({}, "name", "node_name")

    def test_single_key_found(self):
        require_any_param = self._get_helper()
        assert require_any_param({"x": 42}, "x") == 42

    def test_single_key_missing_raises(self):
        from dcc_mcp_maya.api import MissingParamError, require_any_param

        with pytest.raises(MissingParamError):
            require_any_param({}, "x")

    def test_error_message_lists_all_keys(self):
        from dcc_mcp_maya.api import MissingParamError, require_any_param

        with pytest.raises(MissingParamError) as exc_info:
            require_any_param({}, "alpha", "beta", "gamma")
        msg = str(exc_info.value)
        assert "alpha" in msg
        assert "beta" in msg
        assert "gamma" in msg

    def test_reexported_from_package(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "require_any_param")


# ---------------------------------------------------------------------------
# TestGetParamList
# ---------------------------------------------------------------------------


class TestGetParamList:
    """Tests for dcc_mcp_maya.api.get_param_list."""

    def _get_helper(self):
        from dcc_mcp_maya.api import get_param_list

        return get_param_list

    def test_list_value_returned_as_is(self):
        get_param_list = self._get_helper()
        assert get_param_list({"items": ["a", "b"]}, "items") == ["a", "b"]

    def test_string_value_wrapped_in_list(self):
        get_param_list = self._get_helper()
        assert get_param_list({"item": "foo"}, "item") == ["foo"]

    def test_missing_key_returns_default_empty_list(self):
        get_param_list = self._get_helper()
        assert get_param_list({}, "missing") == []

    def test_missing_key_returns_custom_default(self):
        get_param_list = self._get_helper()
        assert get_param_list({}, "missing", ["x"]) == ["x"]

    def test_tuple_value_converted_to_list(self):
        get_param_list = self._get_helper()
        assert get_param_list({"t": ("a", "b")}, "t") == ["a", "b"]

    def test_single_int_wrapped_in_list(self):
        get_param_list = self._get_helper()
        assert get_param_list({"n": 5}, "n") == [5]

    def test_empty_string_gives_one_element_list(self):
        get_param_list = self._get_helper()
        assert get_param_list({"k": ""}, "k") == [""]

    def test_reexported_from_package(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "get_param_list")


# ---------------------------------------------------------------------------
# TestSkinningUtilsRefactor — validate_node_exists / batch_validate_nodes
# ---------------------------------------------------------------------------


class TestSkinningUtilsRefactor:
    """Verify that refactored skinning-utils scripts use api helpers correctly."""

    # --- copy_skin_weights ---

    def test_copy_source_missing(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("missingSource", "targetMesh")
        assert result["success"] is False
        assert "missingSource" in result["message"]

    def test_copy_target_missing(self):
        mock_maya, mock_cmds = _make_mock_maya()

        def exists(name):
            return name == "sourceMesh"

        mock_cmds.objExists.side_effect = exists
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("sourceMesh", "missingTarget")
        assert result["success"] is False
        assert "missingTarget" in result["message"]

    def test_copy_no_skin_cluster_on_source(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = []
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("sourceMesh", "targetMesh")
        assert result["success"] is False
        assert "skin cluster" in result["message"].lower()

    def test_copy_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        mock_cmds.ls.side_effect = lambda *a, **kw: ["skinCluster1"] if kw.get("type") == "skinCluster" else []
        mock_cmds.skinCluster.return_value = ["joint1", "joint2"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "copy_skin_weights")
            result = mod.copy_skin_weights("sourceMesh", "targetMesh")
        assert result["success"] is True
        ctx = result.get("context", {})
        assert ctx.get("source_mesh") == "sourceMesh"
        assert ctx.get("target_mesh") == "targetMesh"

    # --- normalize_skin_weights ---

    def test_normalize_mesh_missing(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.normalize_skin_weights("ghost")
        assert result["success"] is False
        # message should come from validate_node_exists → "Node not found: ghost"
        assert "ghost" in result["message"]

    def test_normalize_no_cluster(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = []
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.normalize_skin_weights("pSphere1")
        assert result["success"] is False

    def test_normalize_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        mock_cmds.ls.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "normalize_skin_weights")
            result = mod.normalize_skin_weights("pSphere1")
        assert result["success"] is True

    # --- mirror_skin_weights ---

    def test_mirror_mesh_missing(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("ghost")
        assert result["success"] is False

    def test_mirror_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        mock_cmds.ls.return_value = ["skinCluster1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("pSphere1")
        assert result["success"] is True
        ctx = result.get("context", {})
        assert ctx.get("mirror_mode") == "YZ"

    def test_mirror_custom_mode(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = ["sc1"]
        mock_cmds.ls.return_value = ["sc1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "mirror_skin_weights")
            result = mod.mirror_skin_weights("pSphere1", mirror_mode="XZ")
        assert result["success"] is True
        assert result["context"]["mirror_mode"] == "XZ"

    # --- prune_skin_weights ---

    def test_prune_mesh_missing(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.prune_skin_weights("ghost")
        assert result["success"] is False

    def test_prune_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = ["sc1"]
        mock_cmds.ls.return_value = ["sc1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.prune_skin_weights("pSphere1", prune_value=0.05)
        assert result["success"] is True
        assert result["context"]["prune_value"] == 0.05

    def test_prune_no_cluster(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listHistory.return_value = []
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-skinning-utils", "prune_skin_weights")
            result = mod.prune_skin_weights("pSphere1")
        assert result["success"] is False
        assert "skin cluster" in result["message"].lower()


# ---------------------------------------------------------------------------
# TestApiPublicExports — verify new helpers visible from top-level package
# ---------------------------------------------------------------------------


class TestApiPublicExports:
    """Smoke-test that all new Round 12 helpers are importable from dcc_mcp_maya."""

    def test_batch_validate_nodes_importable(self):
        from dcc_mcp_maya import batch_validate_nodes

        assert callable(batch_validate_nodes)

    def test_require_any_param_importable(self):
        from dcc_mcp_maya import require_any_param

        assert callable(require_any_param)

    def test_get_param_list_importable(self):
        from dcc_mcp_maya import get_param_list

        assert callable(get_param_list)

    def test_all_helpers_in_dunder_all(self):
        import dcc_mcp_maya

        assert "batch_validate_nodes" in dcc_mcp_maya.__all__
        assert "require_any_param" in dcc_mcp_maya.__all__
        assert "get_param_list" in dcc_mcp_maya.__all__
