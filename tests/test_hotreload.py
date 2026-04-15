"""Tests for hot-reload support in Maya MCP server.

After the DccServerBase refactor, hot-reload is provided by
dcc_mcp_core.hotreload.DccSkillHotReloader.  These tests verify the
integration through the MayaMcpServer API.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
import tempfile
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


class TestDccSkillHotReloaderViaMaya:
    """Tests for DccSkillHotReloader accessed via MayaMcpServer.enable_hot_reload()."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock inner server."""
        server = MagicMock()
        server._server = MagicMock()
        server._server.list_skills.return_value = []
        server._server.load_skill = MagicMock()
        return server

    def _make_reloader(self):
        from dcc_mcp_core.hotreload import DccSkillHotReloader

        return DccSkillHotReloader(dcc_name="maya", server=MagicMock())

    def test_init_creates_reloader(self):
        """DccSkillHotReloader initial state."""
        reloader = self._make_reloader()
        assert reloader._dcc_name == "maya"
        assert reloader.is_enabled is False
        assert reloader.reload_count == 0
        assert reloader.watched_paths == []

    def test_repr_shows_status(self):
        """repr includes dcc name and status."""
        reloader = self._make_reloader()
        r = repr(reloader)
        assert "maya" in r
        assert "disabled" in r

    def test_enable_with_empty_paths_returns_false(self):
        """enable() with no paths returns False."""
        reloader = self._make_reloader()
        result = reloader.enable(skill_paths=[])
        assert result is False
        assert reloader.is_enabled is False

    def test_enable_with_mock_watcher(self):
        """enable() with mocked SkillWatcher succeeds."""
        mock_watcher = MagicMock()
        mock_watcher.watch = MagicMock()

        reloader = self._make_reloader()
        with patch("dcc_mcp_core.hotreload.SkillWatcher", return_value=mock_watcher, create=True):
            with patch("dcc_mcp_core.hotreload.DccSkillHotReloader.enable", return_value=True) as m:
                result = reloader.enable(skill_paths=["/path/to/skills"])
                m.assert_called_once()
                # result is from the mock
                assert result is True

    def test_enable_already_enabled_returns_true(self):
        """Calling enable() twice returns True without error."""
        reloader = self._make_reloader()
        with patch("dcc_mcp_core.hotreload.DccSkillHotReloader.enable", return_value=True):
            result1 = reloader.enable(skill_paths=["/path"])
            result2 = reloader.enable(skill_paths=["/path"])
            assert result1 is True
            assert result2 is True

    def test_disable_is_safe_when_not_enabled(self):
        """disable() must not raise when not enabled."""
        reloader = self._make_reloader()
        reloader.disable()  # should not raise
        assert reloader.is_enabled is False

    def test_reload_now_when_disabled_returns_zero(self):
        """reload_now() returns 0 when hot-reload is not enabled."""
        reloader = self._make_reloader()
        assert reloader.reload_now() == 0

    def test_reload_now_increments_counter(self):
        """reload_now() increments reload_count."""
        reloader = self._make_reloader()
        # Simulate enabled state
        mock_watcher = MagicMock()
        reloader._watcher = mock_watcher
        reloader._enabled = True

        reloader.reload_now()
        assert reloader.reload_count == 1
        reloader.reload_now()
        assert reloader.reload_count == 2

    def test_get_stats_structure(self):
        """get_stats() returns dict with expected keys."""
        reloader = self._make_reloader()
        stats = reloader.get_stats()
        assert "enabled" in stats
        assert "watched_paths" in stats
        assert "reload_count" in stats

    def test_debounce_parameter_passed(self):
        """enable() passes debounce_ms to SkillWatcher."""
        reloader = self._make_reloader()
        with patch("dcc_mcp_core.hotreload.DccSkillHotReloader.enable", return_value=True) as m:
            reloader.enable(skill_paths=["/path"], debounce_ms=500)
            m.assert_called_once_with(skill_paths=["/path"], debounce_ms=500)


class TestMayaServerHotReloadAPI:
    """Test that MayaMcpServer exposes the correct hot-reload interface."""

    def test_enable_hot_reload_method_exists(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "enable_hot_reload")

    def test_disable_hot_reload_method_exists(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "disable_hot_reload")

    def test_is_hot_reload_enabled_property(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "is_hot_reload_enabled")

    def test_hot_reload_stats_property(self):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "hot_reload_stats")


class TestHotReloadIntegration:
    """Integration tests (require optional dependencies)."""

    @pytest.mark.skipif(
        os.environ.get("DCC_MCP_MAYA_SKIP_INTEGRATION") == "1",
        reason="Integration tests skipped",
    )
    def test_skill_watcher_available(self):
        """SkillWatcher can be imported from dcc-mcp-core."""
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
        """DccSkillHotReloader works with a real temporary directory."""
        try:
            from dcc_mcp_core import SkillWatcher  # noqa: F401
        except ImportError:
            pytest.skip("dcc-mcp-core SkillWatcher not available")

        from dcc_mcp_core.hotreload import DccSkillHotReloader

        mock_server = MagicMock()
        mock_server._server = MagicMock()
        mock_server._server.list_skills.return_value = []

        reloader = DccSkillHotReloader(dcc_name="maya", server=mock_server)

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = reloader.enable(skill_paths=[tmp_dir])
            assert result is True
            assert reloader.is_enabled is True
            assert tmp_dir in reloader.watched_paths

            reloader.disable()
            assert reloader.is_enabled is False
