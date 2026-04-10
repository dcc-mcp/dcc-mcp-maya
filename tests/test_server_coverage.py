"""Additional server.py tests to close remaining coverage gaps.

Targets:
- lines 87-91: _BUILTIN_SKILLS_DIR.is_dir() False branch
- lines 97-100: get_skills_dir() default path appended
- lines 172-177: repeating_poll closure (executor poll + recursive deferred)
- lines 233-235: load_skill failure warning path
- line 332: start_server with extra_skill_paths
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
        """When _BUILTIN_SKILLS_DIR does not exist, it is skipped (line 87 False branch)."""
        srv_mod = _import_server()
        # Use a temporary (non-existent) path as the builtin dir so is_dir() returns False
        import pathlib

        fake_builtin = pathlib.Path("/nonexistent/fake/skills/dir")
        with patch.object(srv_mod, "_BUILTIN_SKILLS_DIR", fake_builtin):
            paths = srv_mod._collect_skill_search_paths()
        assert str(fake_builtin) not in paths

    def test_default_skills_dir_appended_when_not_in_paths(self):
        """get_skills_dir() result is appended when not already in paths (lines 97-99)."""
        srv_mod = _import_server()
        sentinel = "/sentinel/default/skills"
        with patch(
            "dcc_mcp_core.get_skills_dir",
            return_value=sentinel,
        ):
            paths = srv_mod._collect_skill_search_paths()
        assert sentinel in paths

    def test_default_skills_dir_not_duplicated(self):
        """get_skills_dir() result is NOT appended if already in paths (line 97 guard)."""
        srv_mod = _import_server()
        builtin = str(srv_mod._BUILTIN_SKILLS_DIR)
        # Make get_skills_dir return the same path as builtin so it won't be appended
        with patch(
            "dcc_mcp_core.get_skills_dir",
            return_value=builtin,
        ):
            paths = srv_mod._collect_skill_search_paths()
        # builtin should appear exactly once even though get_skills_dir returns it
        assert paths.count(builtin) == 1

    def test_default_skills_dir_none_not_appended(self):
        """get_skills_dir() returning None is handled gracefully (line 97 falsy guard)."""
        srv_mod = _import_server()
        with patch("dcc_mcp_core.get_skills_dir", return_value=None):
            paths = srv_mod._collect_skill_search_paths()
        assert None not in paths


# ── repeating_poll closure coverage ───────────────────────────────────────────


class TestRepeatingPollClosure:
    def test_repeating_poll_invokes_executor_poll_pending(self):
        """repeating_poll calls executor.poll_pending() when executor is set (lines 172-177)."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=True)

        # Install a fake executor so the if-branch is taken
        fake_executor = MagicMock()
        server._executor = fake_executor

        # Capture the callback passed to executeDeferred, then invoke it
        import maya.utils

        captured_callbacks = []

        def capture_deferred(fn):
            captured_callbacks.append(fn)

        maya.utils.executeDeferred.side_effect = capture_deferred
        server._setup_poll_callback()

        # The first callback is the initial repeating_poll
        assert len(captured_callbacks) >= 1
        first_cb = captured_callbacks[0]
        # Reset side_effect so the recursive call doesn't keep appending forever
        maya.utils.executeDeferred.side_effect = None
        first_cb()

        # executor.poll_pending() must have been called exactly once
        fake_executor.poll_pending.assert_called_once()

    def test_repeating_poll_executor_none_skips_poll(self):
        """repeating_poll with executor=None skips poll_pending (lines 173-174 False branch)."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=True)
        server._executor = None  # explicitly None

        import maya.utils

        captured_callbacks = []

        def capture_deferred(fn):
            captured_callbacks.append(fn)

        maya.utils.executeDeferred.side_effect = capture_deferred
        server._setup_poll_callback()

        assert len(captured_callbacks) >= 1
        first_cb = captured_callbacks[0]
        maya.utils.executeDeferred.side_effect = None
        # Should complete without error even though executor is None
        first_cb()

    def test_repeating_poll_reschedules_itself(self):
        """repeating_poll calls executeDeferred again to reschedule (line 177)."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=True)

        import maya.utils

        captured_callbacks = []

        def capture_deferred(fn):
            captured_callbacks.append(fn)

        maya.utils.executeDeferred.side_effect = capture_deferred
        server._setup_poll_callback()

        initial_call_count = len(captured_callbacks)
        # Run the first poll callback; it should re-schedule
        maya.utils.executeDeferred.side_effect = capture_deferred
        first_cb = captured_callbacks[0]
        first_cb()

        # One more call from inside repeating_poll (self-reschedule)
        assert len(captured_callbacks) == initial_call_count + 1


# ── load_skill failure path (lines 233-235) ───────────────────────────────────


class TestLoadSkillFailure:
    def test_load_skill_failure_logs_warning_and_continues(self):
        """If load_skill raises, a warning is logged and iteration continues (lines 233-235)."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)

        # McpHttpServer is a Rust extension; replace the entire _server attribute
        # with a MagicMock so we can control discover/list_skills/load_skill.
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

        # Should return self for chaining even when a skill fails
        assert result is server
        # Warning must have been emitted with the skill name
        assert mock_warn.call_count >= 1
        warn_msg = str(mock_warn.call_args_list[0])
        assert "bad_skill" in warn_msg

    def test_load_skill_mixed_success_failure(self):
        """Counts loaded/failed correctly when some skills succeed and some fail."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)

        mock_mcp_server = MagicMock()
        mock_mcp_server.discover.return_value = 2

        good = MagicMock()
        good.name = "good_skill"
        bad = MagicMock()
        bad.name = "bad_skill"
        mock_mcp_server.list_skills.return_value = [good, bad]

        # good_skill loads fine; bad_skill raises
        mock_mcp_server.load_skill.side_effect = [None, RuntimeError("boom")]
        server._server = mock_mcp_server

        result = server.register_builtin_actions()
        assert result is server


# ── start_server with extra_skill_paths (line 332) ────────────────────────────


class TestStartServerExtraSkillPaths:
    def test_start_server_with_extra_skill_paths(self):
        """start_server passes extra_skill_paths to register_builtin_actions (line 332)."""
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
