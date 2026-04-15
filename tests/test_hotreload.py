"""Tests for the MayaSkillHotReloader implementation."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
import tempfile
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya.hotreload import MayaSkillHotReloader


class TestMayaSkillHotReloader:
    """Test suite for MayaSkillHotReloader."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock MayaMcpServer."""
        server = MagicMock()
        server._server = MagicMock()
        server._server.list_skills.return_value = []
        server._server.load_skill = MagicMock()
        return server

    def test_init_creates_reloader(self, mock_server):
        """Test that __init__ creates a reloader instance."""
        reloader = MayaSkillHotReloader(mock_server)
        assert reloader._server is mock_server
        assert reloader.is_enabled is False
        assert reloader.reload_count == 0
        assert reloader.watched_paths == []

    def test_repr_shows_status(self, mock_server):
        """Test __repr__ output format."""
        reloader = MayaSkillHotReloader(mock_server)
        repr_str = repr(reloader)
        assert "MayaSkillHotReloader" in repr_str
        assert "disabled" in repr_str
        assert "reloads=0" in repr_str

    def test_enable_without_explicit_paths_tries_resolve(self, mock_server):
        """Test that enable() with None paths tries to resolve them."""
        mock_watcher = MagicMock()
        reloader = MayaSkillHotReloader(mock_server)

        # When no paths provided, _resolve_skill_paths is called
        # Mock it to return empty list
        with patch.object(reloader, "_resolve_skill_paths", return_value=[]):
            with patch("dcc_mcp_core.SkillWatcher", return_value=mock_watcher):
                result = reloader.enable(skill_paths=None)
                assert result is False
                assert reloader.is_enabled is False

    def test_enable_with_mock_watcher(self, mock_server):
        """Test enable() with mocked SkillWatcher."""
        mock_watcher = MagicMock()
        mock_watcher.watch = MagicMock()

        reloader = MayaSkillHotReloader(mock_server)

        with patch("dcc_mcp_core.SkillWatcher", return_value=mock_watcher):
            result = reloader.enable(skill_paths=["/path/to/skills"])
            assert result is True
            assert reloader.is_enabled is True
            assert len(reloader.watched_paths) == 1
            mock_watcher.watch.assert_called_once_with("/path/to/skills")

    def test_enable_already_enabled_returns_true(self, mock_server):
        """Test that enabling twice returns True without error."""
        mock_watcher = MagicMock()
        reloader = MayaSkillHotReloader(mock_server)

        with patch("dcc_mcp_core.SkillWatcher", return_value=mock_watcher):
            # First enable
            result1 = reloader.enable(skill_paths=["/path"])
            assert result1 is True

            # Second enable (should be no-op)
            result2 = reloader.enable(skill_paths=["/path"])
            assert result2 is True
            assert reloader.is_enabled is True

    def test_disable_clears_state(self, mock_server):
        """Test that disable() clears watched paths and watcher."""
        mock_watcher = MagicMock()
        reloader = MayaSkillHotReloader(mock_server)

        with patch("dcc_mcp_core.SkillWatcher", return_value=mock_watcher):
            reloader.enable(skill_paths=["/path"])
            assert reloader.is_enabled is True

            reloader.disable()
            assert reloader.is_enabled is False
            assert reloader.watched_paths == []
            assert reloader._watcher is None

    def test_reload_now_when_disabled_returns_zero(self, mock_server):
        """Test reload_now() returns 0 when reloader is disabled."""
        reloader = MayaSkillHotReloader(mock_server)
        result = reloader.reload_now()
        assert result == 0

    def test_reload_now_increments_counter(self, mock_server):
        """Test reload_now() increments reload counter."""
        mock_watcher = MagicMock()
        mock_server._server.list_skills.return_value = [
            {"name": "skill1"},
            {"name": "skill2"},
        ]
        reloader = MayaSkillHotReloader(mock_server)

        with patch("dcc_mcp_core.SkillWatcher", return_value=mock_watcher):
            reloader.enable(skill_paths=["/path"])
            assert reloader.reload_count == 0

            reloader.reload_now()
            assert reloader.reload_count == 1

            reloader.reload_now()
            assert reloader.reload_count == 2

    def test_multiple_paths_watched(self, mock_server):
        """Test enable() with multiple paths."""
        mock_watcher = MagicMock()
        reloader = MayaSkillHotReloader(mock_server)

        paths = ["/path1", "/path2", "/path3"]
        with patch("dcc_mcp_core.SkillWatcher", return_value=mock_watcher):
            result = reloader.enable(skill_paths=paths)
            assert result is True
            assert len(reloader.watched_paths) == 3
            assert set(reloader.watched_paths) == set(paths)
            assert mock_watcher.watch.call_count == 3

    def test_debounce_parameter_passed(self, mock_server):
        """Test that debounce_ms parameter is passed to SkillWatcher."""
        mock_watcher = MagicMock()
        reloader = MayaSkillHotReloader(mock_server)

        with patch("dcc_mcp_core.SkillWatcher") as MockWatcher:
            MockWatcher.return_value = mock_watcher
            reloader.enable(skill_paths=["/path"], debounce_ms=500)
            MockWatcher.assert_called_once_with(debounce_ms=500)

    def test_enable_partial_path_failure(self, mock_server):
        """Test enable() when some paths fail to watch."""
        mock_watcher = MagicMock()

        def watch_side_effect(path):
            if path == "/valid/path":
                return None
            raise RuntimeError(f"Cannot watch {path}")

        mock_watcher.watch = MagicMock(side_effect=watch_side_effect)
        reloader = MayaSkillHotReloader(mock_server)

        with patch("dcc_mcp_core.SkillWatcher", return_value=mock_watcher):
            result = reloader.enable(skill_paths=["/invalid/path", "/valid/path"])
            # Should succeed if at least one path was watched
            assert result is True
            assert len(reloader.watched_paths) == 1
            assert reloader.watched_paths[0] == "/valid/path"


class TestMayaSkillHotReloaderIntegration:
    """Integration tests (require optional dependencies)."""

    @pytest.mark.skipif(
        os.environ.get("DCC_MCP_MAYA_SKIP_INTEGRATION") == "1",
        reason="Integration tests skipped",
    )
    def test_skill_watcher_available(self):
        """Test that SkillWatcher can be imported from dcc-mcp-core."""
        try:
            from dcc_mcp_core import SkillWatcher  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("dcc-mcp-core SkillWatcher not available")

    @pytest.mark.skipif(
        os.environ.get("DCC_MCP_MAYA_SKIP_INTEGRATION") == "1",
        reason="Integration tests skipped",
    )
    def test_reloader_with_real_temp_dir(self):
        """Test reloader with a real temporary directory."""
        try:
            from dcc_mcp_core import SkillWatcher  # noqa: F401
        except ImportError:
            pytest.skip("dcc-mcp-core SkillWatcher not available")

        mock_server = MagicMock()
        mock_server._server = MagicMock()
        mock_server._server.list_skills.return_value = []

        reloader = MayaSkillHotReloader(mock_server)

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = reloader.enable(skill_paths=[tmp_dir])
            assert result is True
            assert reloader.is_enabled is True
            assert tmp_dir in reloader.watched_paths

            reloader.disable()
            assert reloader.is_enabled is False
