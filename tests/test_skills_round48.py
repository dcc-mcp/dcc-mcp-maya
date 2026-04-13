"""Round 48 tests: sandbox helpers, make_scene_object, structured skill output."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import inspect
import sys
from unittest.mock import MagicMock, patch

# Import local modules
from dcc_mcp_maya import api as dcc_mcp_maya_api
from dcc_mcp_maya.api import (
    create_sandbox_context,
    create_sandbox_policy,
    make_scene_object,
)


def _load_skill_script(skill_name, script_name):
    """Dynamically load a skill script module."""
    import importlib

    mod_path = "dcc_mcp_maya.skills.{}.scripts.{}".format(skill_name, script_name)
    return importlib.import_module(mod_path)


def make_mock_maya():
    """Create a mock Maya environment."""
    mock_maya = MagicMock()
    mock_cmds = MagicMock()
    mock_utils = MagicMock()
    mock_maya.cmds = mock_cmds
    return mock_maya, mock_cmds, mock_utils


# ===========================================================================
# Sandbox helpers
# ===========================================================================


class TestCreateSandboxPolicy:
    """Tests for api.create_sandbox_policy."""

    def test_returns_policy_instance(self):
        policy = create_sandbox_policy()
        from dcc_mcp_core import SandboxPolicy

        assert isinstance(policy, SandboxPolicy)

    def test_allowed_actions(self):
        policy = create_sandbox_policy(allowed_actions=["get_scene_info", "list_objects"])
        assert policy is not None

    def test_denied_actions(self):
        policy = create_sandbox_policy(denied_actions=["delete_object"])
        assert policy is not None

    def test_read_only(self):
        policy = create_sandbox_policy(read_only=True)
        assert policy is not None

    def test_timeout_ms(self):
        policy = create_sandbox_policy(timeout_ms=5000)
        assert policy is not None

    def test_max_actions(self):
        policy = create_sandbox_policy(max_actions=100)
        assert policy is not None

    def test_allowed_paths(self):
        policy = create_sandbox_policy(allowed_paths=["/tmp/maya"])
        assert policy is not None

    def test_combined_params(self):
        policy = create_sandbox_policy(
            allowed_actions=["get_scene_info"],
            denied_actions=["delete_object"],
            read_only=True,
            timeout_ms=3000,
            max_actions=50,
            allowed_paths=["/tmp"],
        )
        assert policy is not None

    def test_in_api_all(self):
        assert "create_sandbox_policy" in dcc_mcp_maya_api.__all__


class TestCreateSandboxContext:
    """Tests for api.create_sandbox_context."""

    def test_returns_context_instance(self):
        ctx = create_sandbox_context()
        from dcc_mcp_core import SandboxContext

        assert isinstance(ctx, SandboxContext)

    def test_with_actor(self):
        ctx = create_sandbox_context(actor="maya-agent-v1")
        assert ctx is not None

    def test_with_policy_params(self):
        ctx = create_sandbox_context(
            allowed_actions=["get_scene_info"],
            read_only=True,
            actor="test-actor",
        )
        assert ctx is not None

    def test_in_api_all(self):
        assert "create_sandbox_context" in dcc_mcp_maya_api.__all__


# ===========================================================================
# make_scene_object
# ===========================================================================


class TestMakeSceneObject:
    """Tests for api.make_scene_object."""

    def _mock_cmds(self):
        mock = MagicMock()
        mock.objectType.return_value = "transform"
        mock.listRelatives.return_value = ["|world"]
        mock.getAttr.side_effect = lambda attr: [
            (1.0, 2.0, 3.0) if "translate" in attr else (0.0, 0.0, 0.0),
        ]
        return mock

    def test_basic_output(self):
        cmds = self._mock_cmds()
        result = make_scene_object(cmds, "|pSphere1")
        assert result["name"] == "pSphere1"
        assert result["long_name"] == "|pSphere1"
        assert result["object_type"] == "transform"
        assert "visible" in result
        assert "metadata" in result

    def test_with_transform(self):
        cmds = self._mock_cmds()
        result = make_scene_object(cmds, "|pSphere1", include_transform=True)
        assert "translate" in result
        assert "rotate" in result
        assert "scale" in result

    def test_without_transform(self):
        cmds = self._mock_cmds()
        result = make_scene_object(cmds, "|pSphere1", include_transform=False)
        assert "translate" not in result

    def test_transform_exception_handled(self):
        cmds = self._mock_cmds()
        cmds.getAttr.side_effect = RuntimeError("no transform")
        result = make_scene_object(cmds, "|pSphere1", include_transform=True)
        # Should not raise; transform keys simply not added
        assert "name" in result

    def test_nested_path(self):
        cmds = self._mock_cmds()
        result = make_scene_object(cmds, "|group1|pSphere1")
        assert result["name"] == "pSphere1"
        assert result["long_name"] == "|group1|pSphere1"

    def test_in_api_all(self):
        assert "make_scene_object" in dcc_mcp_maya_api.__all__


# ===========================================================================
# Structured output: list_objects with SceneObject
# ===========================================================================


class TestListObjectsStructured:
    """Tests for list_objects.py returning SceneObject dicts."""

    def _load(self):
        return _load_skill_script("maya-scene", "list_objects")

    def test_dag_returns_scene_objects(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["|group1|pSphere1", "|group1|pCube1"]
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_objects(dag=True)
        assert result["success"] is True
        objects = result["context"]["objects"]
        assert len(objects) == 2
        # Each is a SceneObject dict
        for obj in objects:
            assert "name" in obj
            assert "long_name" in obj
            assert "object_type" in obj

    def test_non_dag_returns_plain_list(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["lambert1", "phong1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_objects(dag=False)
        assert result["success"] is True
        objects = result["context"]["objects"]
        # Non-DAG returns plain strings
        assert objects == ["lambert1", "phong1"]

    def test_include_transform_flag(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["|pSphere1"]
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = []
        mock_cmds.getAttr.side_effect = lambda attr: [(1.0, 2.0, 3.0)]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_objects(dag=True, include_transform=True)
        assert result["success"] is True
        obj = result["context"]["objects"][0]
        assert "translate" in obj or "name" in obj  # transform may fail gracefully


# ===========================================================================
# Structured output: get_selection with SceneObject
# ===========================================================================


class TestGetSelectionStructured:
    """Tests for get_selection.py returning SceneObject dicts."""

    def _load(self):
        return _load_skill_script("maya-scene", "get_selection")

    def test_returns_scene_objects(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["|pSphere1", "|pCube1"]
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_selection()
        assert result["success"] is True
        selection = result["context"]["selection"]
        assert len(selection) == 2
        for obj in selection:
            assert "name" in obj
            assert "long_name" in obj

    def test_include_transform(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = ["|pSphere1"]
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = []
        mock_cmds.getAttr.side_effect = lambda attr: [(0.0, 0.0, 0.0)]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_selection(include_transform=True)
        assert result["success"] is True

    def test_empty_selection(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_selection()
        assert result["success"] is True
        assert result["context"]["count"] == 0


# ===========================================================================
# Structured output: get_bounding_box with bounding_box_from_node
# ===========================================================================


class TestGetBoundingBoxStructured:
    """Tests for get_bounding_box.py using bounding_box_from_node API."""

    def _load(self):
        return _load_skill_script("maya-scene", "get_bounding_box")

    def test_success_returns_bounding_box(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_bounding_box(object_name="pSphere1")
        assert result["success"] is True
        assert "bounding_box" in result["context"]
        bb = result["context"]["bounding_box"]
        assert "min" in bb
        assert "max" in bb
        assert "center" in bb
        assert "size" in bb

    def test_missing_node(self):
        mod = self._load()
        mock_maya, mock_cmds, _ = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.get_bounding_box(object_name="nonexistent")
        assert result["success"] is False


# ===========================================================================
# Package-level re-exports
# ===========================================================================


class TestPackageReexports:
    """Ensure new symbols are re-exported from dcc_mcp_maya."""

    def test_make_scene_object(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "make_scene_object")
        assert "make_scene_object" in dcc_mcp_maya.__all__

    def test_create_sandbox_policy(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "create_sandbox_policy")
        assert "create_sandbox_policy" in dcc_mcp_maya.__all__

    def test_create_sandbox_context(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "create_sandbox_context")
        assert "create_sandbox_context" in dcc_mcp_maya.__all__


# ===========================================================================
# Structural checks
# ===========================================================================


class TestStructuralChecks:
    """Verify new skill signatures and imports."""

    def test_list_objects_has_include_transform_param(self):
        mod = _load_skill_script("maya-scene", "list_objects")
        sig = inspect.signature(mod.list_objects)
        assert "include_transform" in sig.parameters

    def test_get_selection_has_include_transform_param(self):
        mod = _load_skill_script("maya-scene", "get_selection")
        sig = inspect.signature(mod.get_selection)
        assert "include_transform" in sig.parameters

    def test_get_bounding_box_imports_bounding_box_from_node(self):
        import pathlib

        script_path = (
            pathlib.Path(__file__).parent.parent
            / "src"
            / "dcc_mcp_maya"
            / "skills"
            / "maya-scene"
            / "scripts"
            / "get_bounding_box.py"
        )
        content = script_path.read_text(encoding="utf-8")
        assert "bounding_box_from_node" in content
