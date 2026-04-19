"""Tests for plugin env-var export (issue #63).

Verifies that ``_export_worker_env()`` in the Maya plugin correctly exports
``DCC_MCP_PYTHON_EXECUTABLE`` and ``DCC_MCP_PYTHON_INIT_SNIPPET`` so that
skill worker subprocesses use the correct Maya Python interpreter.

See: https://github.com/loonghao/dcc-mcp-maya/issues/63
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# Path to the plugin file
_PLUGIN_PATH = Path(__file__).parent.parent / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"


@pytest.fixture(autouse=True)
def mock_maya_modules():
    """Inject minimal maya stubs so the plugin can be imported without Maya."""
    maya_mock = MagicMock()
    maya_mock.cmds = MagicMock()
    maya_mock.cmds.about.return_value = "2025"
    maya_mock.mel = MagicMock()
    maya_mock.utils = MagicMock()
    maya_mock.api = MagicMock()
    maya_mock.api.OpenMaya = MagicMock()

    mods = {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": maya_mock.mel,
        "maya.utils": maya_mock.utils,
        "maya.api": maya_mock.api,
        "maya.api.OpenMaya": maya_mock.api.OpenMaya,
    }
    with patch.dict(sys.modules, mods):
        yield maya_mock


@pytest.fixture
def plugin_module(mock_maya_modules):
    """Import the plugin script as a plain Python module."""
    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_plugin", _PLUGIN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestExportWorkerEnv:
    """Tests for ``_export_worker_env()``."""

    def test_sets_python_executable(self, plugin_module):
        """Should set DCC_MCP_PYTHON_EXECUTABLE to sys.executable."""
        env = os.environ.copy()
        env.pop("DCC_MCP_PYTHON_EXECUTABLE", None)
        env.pop("DCC_MCP_PYTHON_INIT_SNIPPET", None)

        with patch.dict(os.environ, env, clear=True):
            plugin_module._export_worker_env()
            assert os.environ["DCC_MCP_PYTHON_EXECUTABLE"] == sys.executable

    def test_sets_init_snippet(self, plugin_module):
        """Should set DCC_MCP_PYTHON_INIT_SNIPPET for maya.standalone init."""
        env = os.environ.copy()
        env.pop("DCC_MCP_PYTHON_EXECUTABLE", None)
        env.pop("DCC_MCP_PYTHON_INIT_SNIPPET", None)

        with patch.dict(os.environ, env, clear=True):
            plugin_module._export_worker_env()
            snippet = os.environ["DCC_MCP_PYTHON_INIT_SNIPPET"]
            assert "maya.standalone" in snippet
            assert "initialize" in snippet

    def test_respects_existing_executable_override(self, plugin_module):
        """Should NOT overwrite if user already set the env var."""
        custom_path = "/custom/mayapy"
        env = os.environ.copy()
        env["DCC_MCP_PYTHON_EXECUTABLE"] = custom_path
        env.pop("DCC_MCP_PYTHON_INIT_SNIPPET", None)

        with patch.dict(os.environ, env, clear=True):
            plugin_module._export_worker_env()
            assert os.environ["DCC_MCP_PYTHON_EXECUTABLE"] == custom_path

    def test_respects_existing_snippet_override(self, plugin_module):
        """Should NOT overwrite if user already set the init snippet."""
        custom_snippet = "print('custom init')"
        env = os.environ.copy()
        env.pop("DCC_MCP_PYTHON_EXECUTABLE", None)
        env["DCC_MCP_PYTHON_INIT_SNIPPET"] = custom_snippet

        with patch.dict(os.environ, env, clear=True):
            plugin_module._export_worker_env()
            assert os.environ["DCC_MCP_PYTHON_INIT_SNIPPET"] == custom_snippet

    def test_both_vars_set_simultaneously(self, plugin_module):
        """Both env vars should be set after a single call."""
        env = os.environ.copy()
        env.pop("DCC_MCP_PYTHON_EXECUTABLE", None)
        env.pop("DCC_MCP_PYTHON_INIT_SNIPPET", None)

        with patch.dict(os.environ, env, clear=True):
            plugin_module._export_worker_env()
            assert "DCC_MCP_PYTHON_EXECUTABLE" in os.environ
            assert "DCC_MCP_PYTHON_INIT_SNIPPET" in os.environ
