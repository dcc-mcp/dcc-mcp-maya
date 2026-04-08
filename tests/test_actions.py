"""Tests for Maya action functions (maya.cmds is mocked)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


@pytest.fixture(autouse=True)
def mock_maya():
    """Inject a minimal maya stub."""
    cmds_mock = MagicMock()
    mel_mock = MagicMock()

    # Default return values for common calls
    cmds_mock.file.return_value = "/tmp/test.mb"
    cmds_mock.ls.return_value = ["pSphere1", "pCube1"]
    cmds_mock.polySphere.return_value = ["pSphere1", "polySphere1"]
    cmds_mock.polyCube.return_value = ["pCube1", "polyCube1"]
    cmds_mock.polyCylinder.return_value = ["pCylinder1", "polyCylinder1"]
    cmds_mock.rename.side_effect = lambda obj, name: name
    cmds_mock.objExists.return_value = True
    cmds_mock.about.return_value = "2025"
    cmds_mock.currentUnit.return_value = "film"
    cmds_mock.upAxis.return_value = "y"
    mel_mock.eval.return_value = None

    with patch.dict(
        sys.modules,
        {
            "maya": MagicMock(cmds=cmds_mock, mel=mel_mock, utils=MagicMock()),
            "maya.cmds": cmds_mock,
            "maya.mel": mel_mock,
            "maya.utils": MagicMock(),
        },
    ):
        yield cmds_mock, mel_mock


def _reload_actions():
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]


class TestSceneActions:
    def test_new_scene_success(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.scene import new_scene

        result = new_scene()
        assert result["success"] is True

    def test_save_scene_returns_path(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.scene import save_scene

        result = save_scene()
        assert result["success"] is True
        assert "file_path" in result["context"]

    def test_list_objects_returns_names(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.scene import list_objects

        result = list_objects()
        assert result["success"] is True
        assert "objects" in result["context"]
        assert len(result["context"]["objects"]) == 2

    def test_get_selection_returns_list(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.scene import get_selection

        result = get_selection()
        assert result["success"] is True
        assert "selection" in result["context"]

    def test_set_selection_calls_cmds(self, mock_maya):
        _reload_actions()
        cmds_mock, _ = mock_maya
        from dcc_mcp_maya.actions.scene import set_selection

        result = set_selection(["pSphere1"])
        assert result["success"] is True
        cmds_mock.select.assert_called_once_with(["pSphere1"], replace=True)

    def test_get_session_info_has_version(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.scene import get_session_info

        result = get_session_info()
        assert result["success"] is True
        assert "maya_version" in result["context"]

    def test_new_scene_no_maya(self):
        """Returns error result when maya is not available."""
        _reload_actions()
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            # Temporarily remove maya from modules so ImportError is triggered
            original_cmds = sys.modules.pop("maya.cmds", None)
            original_maya = sys.modules.pop("maya", None)
            try:
                sys.modules["maya.cmds"] = None  # type: ignore[assignment]
                sys.modules["maya"] = None  # type: ignore[assignment]
                for mod in list(sys.modules):
                    if "dcc_mcp_maya.actions" in mod:
                        del sys.modules[mod]
                from dcc_mcp_maya.actions.scene import new_scene

                result = new_scene()
                assert result["success"] is False
            finally:
                if original_cmds is not None:
                    sys.modules["maya.cmds"] = original_cmds
                if original_maya is not None:
                    sys.modules["maya"] = original_maya


class TestPrimitiveActions:
    def test_create_sphere(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.primitives import create_sphere

        result = create_sphere(radius=2.0)
        assert result["success"] is True
        assert result["context"]["radius"] == 2.0

    def test_create_sphere_with_name(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.primitives import create_sphere

        result = create_sphere(name="mySphere")
        assert result["success"] is True
        assert result["context"]["object_name"] == "mySphere"

    def test_create_cube(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.primitives import create_cube

        result = create_cube(width=2.0, height=3.0, depth=4.0)
        assert result["success"] is True
        assert result["context"]["width"] == 2.0

    def test_create_cylinder(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.primitives import create_cylinder

        result = create_cylinder(radius=1.5, height=4.0)
        assert result["success"] is True
        assert result["context"]["radius"] == 1.5

    def test_delete_objects(self, mock_maya):
        _reload_actions()
        cmds_mock, _ = mock_maya
        from dcc_mcp_maya.actions.primitives import delete_objects

        result = delete_objects(["pSphere1"])
        assert result["success"] is True
        cmds_mock.delete.assert_called()

    def test_delete_empty_list(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.primitives import delete_objects

        result = delete_objects([])
        assert result["success"] is True

    def test_set_transform_translate(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.primitives import set_transform

        result = set_transform("pSphere1", translate=[1.0, 2.0, 3.0])
        assert result["success"] is True
        assert "translate" in result["context"]

    def test_set_transform_object_not_found(self, mock_maya):
        _reload_actions()
        cmds_mock, _ = mock_maya
        cmds_mock.objExists.return_value = False
        from dcc_mcp_maya.actions.primitives import set_transform

        result = set_transform("nonexistent")
        assert result["success"] is False


class TestScriptingActions:
    def test_execute_mel_success(self, mock_maya):
        _reload_actions()
        _, mel_mock = mock_maya
        mel_mock.eval.return_value = "done"
        from dcc_mcp_maya.actions.scripting import execute_mel

        result = execute_mel("sphere;")
        assert result["success"] is True
        assert "output" in result["context"]

    def test_execute_mel_error(self, mock_maya):
        _reload_actions()
        _, mel_mock = mock_maya
        mel_mock.eval.side_effect = RuntimeError("MEL error")
        from dcc_mcp_maya.actions.scripting import execute_mel

        result = execute_mel("bad_mel_script")
        assert result["success"] is False

    def test_execute_python_success(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.scripting import execute_python

        result = execute_python("result = 2 + 2")
        assert result["success"] is True
        assert result["context"]["output"] == "4"

    def test_execute_python_syntax_error(self, mock_maya):
        _reload_actions()
        from dcc_mcp_maya.actions.scripting import execute_python

        result = execute_python("def (broken")
        assert result["success"] is False


class TestRegisterAll:
    def test_register_all_populates_registry(self):
        _reload_actions()
        from dcc_mcp_core import ActionRegistry

        from dcc_mcp_maya.actions import register_all

        reg = ActionRegistry()
        register_all(reg)
        actions = reg.list_actions()
        names = {a["name"] for a in actions}
        assert "create_sphere" in names
        assert "execute_mel" in names
        assert "execute_python" in names
        assert "get_session_info" in names
        assert len(actions) >= 14
