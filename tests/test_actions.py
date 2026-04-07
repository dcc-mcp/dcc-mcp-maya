"""Tests for Maya actions using mocked maya.cmds."""

# Import built-in modules
from types import ModuleType
from unittest.mock import MagicMock
from unittest.mock import patch
import sys

# Import third-party modules
import pytest


def _mock_maya_cmds(**overrides):
    """Create a MagicMock for maya.cmds with sensible defaults."""
    mock = MagicMock()
    mock.polySphere.return_value = ["pSphere1", "polySphere1"]
    mock.polyCube.return_value = ["pCube1", "polyCube1"]
    mock.polyCylinder.return_value = ["pCylinder1", "polyCylinder1"]
    mock.ls.return_value = []
    mock.file.return_value = "/tmp/test.mb"
    mock.about.side_effect = lambda **kw: "2024" if kw.get("version") else "unknown"
    mock.workspace.return_value = "/tmp/project"
    for k, v in overrides.items():
        setattr(mock, k, v)
    return mock


@pytest.fixture(autouse=True)
def patch_maya(monkeypatch):
    """Inject mock maya modules so tests run without Maya installed."""
    maya_mod = ModuleType("maya")
    maya_cmds_mod = _mock_maya_cmds()
    maya_mel_mod = MagicMock()
    maya_mel_mod.eval.return_value = None

    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", maya_cmds_mod)
    monkeypatch.setitem(sys.modules, "maya.mel", maya_mel_mod)
    monkeypatch.setattr("maya.cmds", maya_cmds_mod, raising=False)

    yield maya_cmds_mod, maya_mel_mod


class TestSceneActions:
    def test_list_objects(self, patch_maya):
        cmds_mock, _ = patch_maya
        cmds_mock.ls.return_value = ["pSphere1", "pCube1"]

        from dcc_mcp_maya.actions.scene import list_objects
        result = list_objects()
        assert result.success is True
        assert result.context["count"] == 2

    def test_get_selection_empty(self, patch_maya):
        cmds_mock, _ = patch_maya
        cmds_mock.ls.return_value = []

        from dcc_mcp_maya.actions.scene import get_selection
        result = get_selection()
        assert result.success is True
        assert result.context["selection"] == []


class TestPrimitiveActions:
    def test_create_sphere(self, patch_maya):
        cmds_mock, _ = patch_maya

        from dcc_mcp_maya.actions.primitives import create_sphere
        result = create_sphere(radius=2.0)
        assert result.success is True
        assert "transform" in result.context
        cmds_mock.polySphere.assert_called_once_with(radius=2.0)

    def test_create_cube(self, patch_maya):
        cmds_mock, _ = patch_maya

        from dcc_mcp_maya.actions.primitives import create_cube
        result = create_cube(width=1.0, height=2.0, depth=3.0)
        assert result.success is True
        cmds_mock.polyCube.assert_called_once_with(width=1.0, height=2.0, depth=3.0)

    def test_delete_empty_list(self, patch_maya):
        from dcc_mcp_maya.actions.primitives import delete_objects
        result = delete_objects([])
        assert result.success is True


class TestMelActions:
    def test_execute_mel(self, patch_maya):
        _, mel_mock = patch_maya
        mel_mock.eval.return_value = "ok"

        from dcc_mcp_maya.actions.mel import execute_mel
        result = execute_mel("polySphere -r 1;")
        assert result.success is True
        assert result.context["result"] == "ok"
