"""Additional server.py tests to close remaining coverage gaps.

Targets:
- collect_skill_search_paths edge cases
- register_builtin_actions progressive discovery behavior
- start_server with extra_skill_paths
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


@pytest.fixture(autouse=True)
def mock_maya_modules():
    """Inject minimal maya stubs."""
    maya_mock = MagicMock()
    maya_mock.cmds = MagicMock()
    maya_mock.mel = MagicMock()
    maya_mock.utils = MagicMock()
    mods = {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": maya_mock.mel,
        "maya.utils": maya_mock.utils,
    }
    with patch.dict(sys.modules, mods):
        yield maya_mock


def _import_server():
    import importlib

    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    return importlib.import_module("dcc_mcp_maya.server")


# ── collect_skill_search_paths coverage ───────────────────────────────────────


def _make_bare_server(builtin_dir=None):
    """Create a MayaMcpServer without __init__ for path-collection tests."""
    from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR, MayaMcpServer

    srv = object.__new__(MayaMcpServer)
    srv._dcc_name = "maya"
    srv._builtin_skills_dir = builtin_dir if builtin_dir is not None else _BUILTIN_SKILLS_DIR
    srv._handle = None
    srv._enable_gateway_failover = False
    srv._hot_reloader = None
    srv._gateway_election = None
    from dcc_mcp_core import McpHttpConfig

    srv._config = McpHttpConfig()
    srv._server = MagicMock()
    # DccServerBase.register_builtin_actions touches these attributes; normally
    # populated by DccServerBase.__init__, which we bypass here.
    srv._dcc_dispatcher = None
    srv._standalone_main_thread = False
    srv._execution_bridge = None
    srv._inprocess_executor_registered = False
    srv._skill_client = MagicMock()
    srv._skill_client.clear_skill_load_transform.return_value = True
    return srv


class TestCollectSkillSearchPathsCoverage:
    def test_builtin_dir_not_a_directory_is_skipped(self):
        """When builtin_skills_dir does not exist, it is skipped."""
        import pathlib

        fake_builtin = pathlib.Path("/nonexistent/fake/skills/dir")
        srv = _make_bare_server(builtin_dir=fake_builtin)
        with patch("dcc_mcp_core.get_app_skill_paths_from_env", return_value=[]), patch(
            "dcc_mcp_core._core.get_skill_paths_from_env", return_value=[], create=True
        ), patch("dcc_mcp_core._server.skill_discovery.get_skills_dir", return_value=None):
            paths = srv.collect_skill_search_paths(include_bundled=False)
        assert str(fake_builtin) not in paths

    def test_default_skills_dir_appended_when_not_in_paths(self):
        """get_skills_dir() result is appended when not already in paths."""
        sentinel = "/sentinel/default/skills"
        srv = _make_bare_server()
        with patch("dcc_mcp_core._server.skill_discovery.get_skills_dir", return_value=sentinel), patch(
            "dcc_mcp_core.get_app_skill_paths_from_env", return_value=[]
        ), patch("dcc_mcp_core.get_skill_paths_from_env", return_value=[]):
            paths = srv.collect_skill_search_paths(include_bundled=False)
        assert sentinel in paths

    def test_default_skills_dir_not_duplicated(self):
        """get_skills_dir() result is NOT appended if already in paths."""
        from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR

        builtin = str(_BUILTIN_SKILLS_DIR)
        srv = _make_bare_server()
        with patch("dcc_mcp_core.get_app_skill_paths_from_env", return_value=[]), patch(
            "dcc_mcp_core._core.get_skill_paths_from_env", return_value=[], create=True
        ), patch("dcc_mcp_core._server.skill_discovery.get_skills_dir", return_value=builtin):
            paths = srv.collect_skill_search_paths(include_bundled=False)
        assert paths.count(builtin) == 1

    def test_default_skills_dir_none_not_appended(self):
        """get_skills_dir() returning None is handled gracefully."""
        srv = _make_bare_server()
        with patch("dcc_mcp_core.get_app_skill_paths_from_env", return_value=[]), patch(
            "dcc_mcp_core._core.get_skill_paths_from_env", return_value=[], create=True
        ), patch("dcc_mcp_core._server.skill_discovery.get_skills_dir", return_value=None):
            paths = srv.collect_skill_search_paths(include_bundled=False)
        assert None not in paths


# ── load_skill failure path ────────────────────────────────────────────────────


class TestLoadSkillFailure:
    def test_register_builtin_actions_discovers_without_loading_skills(self):
        """register_builtin_actions with minimal=False only discovers, no eager load."""
        server = _make_bare_server()

        mock_mcp_server = MagicMock()
        mock_mcp_server.list_skills.return_value = []
        server._server = mock_mcp_server

        result = server.register_builtin_actions(minimal=False)
        assert result is server
        assert server._registration_report.success is True
        mock_mcp_server.load_skill.assert_not_called()

    def test_register_builtin_actions_keeps_working_when_discover_succeeds(self):
        """register_builtin_actions should return self after successful discovery."""
        server = _make_bare_server()

        mock_mcp_server = MagicMock()
        server._server = mock_mcp_server

        result = server.register_builtin_actions()
        assert result is server
        assert server._registration_report.success is True


# ── start_server with extra_skill_paths ───────────────────────────────────────


class TestStartServerExtraSkillPaths:
    def test_start_server_with_extra_skill_paths(self):
        """start_server passes extra_skill_paths to register_builtin_actions."""
        srv_mod = _import_server()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                srv_mod.MayaMcpServer,
                "register_builtin_actions",
                wraps=None,
            ) as mock_reg:
                mock_reg.return_value = MagicMock()
                srv_mod.start_server(
                    port=0,
                    register_builtins=True,
                    extra_skill_paths=[tmp],
                )
            srv_mod.stop_server()

        mock_reg.assert_called_once_with(
            extra_skill_paths=[tmp],
            include_bundled=True,
            minimal=None,
        )

    def test_start_server_register_builtins_false_skips_register(self):
        """start_server with register_builtins=False must not call register_builtin_actions."""
        srv_mod = _import_server()
        with patch.object(
            srv_mod.MayaMcpServer,
            "register_builtin_actions",
        ) as mock_reg:
            srv_mod.start_server(port=0, register_builtins=False)
            srv_mod.stop_server()

        mock_reg.assert_not_called()
