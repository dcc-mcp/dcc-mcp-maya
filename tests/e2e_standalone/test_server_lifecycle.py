"""Maya standalone E2E tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


class TestServerLifecycle:
    """MayaMcpServer starts, reports a valid URL, and stops cleanly."""

    def test_start_and_stop(self):
        from dcc_mcp_maya.server import MayaMcpServer

        server = MayaMcpServer(port=0)
        server.register_builtin_actions()
        handle = server.start()

        assert handle is not None
        url = handle.mcp_url()
        assert url.startswith("http://")
        assert "/mcp" in url

        server.stop()
        assert not server.is_running

    def test_singleton_start_server(self):
        from dcc_mcp_maya import start_server, stop_server

        handle = start_server(port=0)
        assert handle is not None
        stop_server()

    def test_skills_discovered(self):
        """Skills are discovered via SKILL.md (progressive loading — discovered, not loaded)."""
        from dcc_mcp_maya.server import MayaMcpServer

        server = MayaMcpServer(port=0)
        server.register_builtin_actions()
        # Progressive loading: discover() finds skills but does NOT load them.
        # list_skills() returns all discovered skills regardless of status.
        all_skills = {s.name if hasattr(s, "name") else s["name"] for s in server._server.list_skills()}
        # Key skills must be discoverable
        assert "maya-scripting" in all_skills
        assert "maya-scene" in all_skills
        assert "maya-render" in all_skills
        assert len(all_skills) >= 12
