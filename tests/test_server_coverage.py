"""Additional server.py tests to close remaining coverage gaps.

Targets:
- lines 87-91: _BUILTIN_SKILLS_DIR.is_dir() False branch
- lines 97-100: get_skills_dir() default path appended
- lines 233-235: load_skill failure warning path
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


# ── _collect_skill_search_paths coverage ──────────────────────────────────────


class TestCollectSkillSearchPathsCoverage:
    def test_builtin_dir_not_a_directory_is_skipped(self):
        """When _BUILTIN_SKILLS_DIR does not exist, it is skipped (False branch)."""
        srv_mod = _import_server()
        import pathlib

        fake_builtin = pathlib.Path("/nonexistent/fake/skills/dir")
        with patch.object(srv_mod, "_BUILTIN_SKILLS_DIR", fake_builtin):
            paths = srv_mod._collect_skill_search_paths()
        assert str(fake_builtin) not in paths

    def test_default_skills_dir_appended_when_not_in_paths(self):
        """get_skills_dir() result is appended when not already in paths."""
        srv_mod = _import_server()
        sentinel = "/sentinel/default/skills"
        with patch(
            "dcc_mcp_core.get_skills_dir",
            return_value=sentinel,
        ):
            paths = srv_mod._collect_skill_search_paths()
        assert sentinel in paths

    def test_default_skills_dir_not_duplicated(self):
        """get_skills_dir() result is NOT appended if already in paths."""
        srv_mod = _import_server()
        builtin = str(srv_mod._BUILTIN_SKILLS_DIR)
        with patch(
            "dcc_mcp_core.get_skills_dir",
            return_value=builtin,
        ):
            paths = srv_mod._collect_skill_search_paths()
        assert paths.count(builtin) == 1

    def test_default_skills_dir_none_not_appended(self):
        """get_skills_dir() returning None is handled gracefully."""
        srv_mod = _import_server()
        with patch("dcc_mcp_core.get_skills_dir", return_value=None):
            paths = srv_mod._collect_skill_search_paths()
        assert None not in paths


# ── load_skill failure path ────────────────────────────────────────────────────


class TestLoadSkillFailure:
    def test_load_skill_failure_logs_warning_and_continues(self):
        """If load_skill raises, a warning is logged and iteration continues."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)

        mock_mcp_server = MagicMock()
        mock_mcp_server.discover.return_value = 1
        bad_summary = MagicMock()
        bad_summary.name = "bad_skill"
        mock_mcp_server.list_skills.return_value = [bad_summary]
        mock_mcp_server.load_skill.side_effect = RuntimeError("broken skill")
        server._server = mock_mcp_server

        import logging

        with patch.object(logging.getLogger("dcc_mcp_maya.server"), "warning") as mock_warn:
            result = server.register_builtin_actions()

        assert result is server
        assert mock_warn.call_count >= 1
        warn_msg = str(mock_warn.call_args_list[0])
        assert "bad_skill" in warn_msg

    def test_load_skill_mixed_success_failure(self):
        """Counts loaded/failed correctly when some skills succeed and some fail."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)

        mock_mcp_server = MagicMock()
        mock_mcp_server.discover.return_value = 2

        good = MagicMock()
        good.name = "good_skill"
        bad = MagicMock()
        bad.name = "bad_skill"
        mock_mcp_server.list_skills.return_value = [good, bad]
        mock_mcp_server.load_skill.side_effect = [None, RuntimeError("boom")]
        server._server = mock_mcp_server

        result = server.register_builtin_actions()
        assert result is server


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

        mock_reg.assert_called_once_with(extra_skill_paths=[tmp])

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
