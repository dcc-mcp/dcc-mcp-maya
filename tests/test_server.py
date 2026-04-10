"""Tests for MayaMcpServer (no real Maya required — maya.cmds is mocked)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import sys
import urllib.request
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# ── mock maya.cmds at import time ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_maya_modules():
    """Inject a minimal maya stub so imports succeed without a real Maya."""
    maya_mock = MagicMock()
    maya_mock.cmds = MagicMock()
    maya_mock.mel = MagicMock()
    maya_mock.utils = MagicMock()

    modules_to_patch = {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": maya_mock.mel,
        "maya.utils": maya_mock.utils,
    }
    with patch.dict(sys.modules, modules_to_patch):
        yield maya_mock


# ── imports (after mock is in place) ─────────────────────────────────────────


def _import_server():
    # Force reimport so the mock is in effect
    import importlib

    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    srv = importlib.import_module("dcc_mcp_maya.server")
    return srv


def _builtin_skills_dir():
    """Return the built-in skills directory, resolving it from the package."""
    from pathlib import Path

    import dcc_mcp_maya

    return str(Path(dcc_mcp_maya.__file__).parent / "skills")


# ── MayaMcpServer unit tests ──────────────────────────────────────────────────


class TestMayaMcpServerApi:
    def test_start_stop(self):
        """Server starts, returns a handle with mcp_url, then stops."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions()
        handle = server.start()
        assert handle is not None
        url = handle.mcp_url()
        assert url.startswith("http://127.0.0.1:")
        assert server.is_running
        server.stop()
        assert not server.is_running

    def test_double_start_returns_same_handle(self):
        """Calling start() twice returns the same handle."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        h1 = server.start()
        h2 = server.start()
        assert h1 is h2
        server.stop()

    def test_registry_has_builtins(self):
        """register_builtin_actions loads skills into the SkillCatalog."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        # Pass explicit skills path to ensure discovery regardless of install mode
        server.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        # Verify skills are loaded via the SkillCatalog API
        loaded_skills = [
            s.name if hasattr(s, "name") else s["name"] for s in server._server.list_skills(status="loaded")
        ]
        assert "maya-primitives" in loaded_skills
        assert "maya-scripting" in loaded_skills
        assert "maya-scene" in loaded_skills

    def test_mcp_url_none_when_not_running(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        assert server.mcp_url is None


class TestMayaMcpServerHttp:
    """End-to-end HTTP tests against a real McpHttpServer (no Maya needed)."""

    @pytest.fixture
    def running_server(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        # Pass explicit skills path to ensure discovery regardless of install mode
        server.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        handle = server.start()
        yield server, handle
        server.stop()

    def _post(self, url, body):
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())

    def test_initialize(self, running_server):
        _, handle = running_server
        code, body = self._post(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1.0"},
                },
            },
        )
        assert code == 200
        assert body["result"]["serverInfo"]["name"] == "maya-mcp"
        assert body["result"]["protocolVersion"] == "2025-03-26"

    def test_tools_list_contains_maya_actions(self, running_server):
        _, handle = running_server
        code, body = self._post(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
            },
        )
        assert code == 200
        names = {t["name"] for t in body["result"]["tools"]}
        # Skills SOP: action names follow {skill_name}__{script_stem}
        assert "maya_primitives__create_sphere" in names
        assert "maya_scripting__execute_mel" in names
        assert "maya_scene__list_objects" in names
        assert "maya_scene__get_session_info" in names

    def test_tools_call_dispatches_action(self, running_server):
        _, handle = running_server
        code, body = self._post(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "create_sphere", "arguments": {"radius": 2.0}},
            },
        )
        assert code == 200
        # Action is registered and route returns (even if Maya mock returns None)
        result = body["result"]
        assert "content" in result


class TestSkillSearchPaths:
    """_collect_skill_search_paths respects all path sources."""

    def test_builtin_skills_always_included(self):
        srv_mod = _import_server()
        paths = srv_mod._collect_skill_search_paths()
        builtin = str(srv_mod._BUILTIN_SKILLS_DIR)
        assert builtin in paths

    def test_extra_paths_take_highest_priority(self):
        import tempfile

        srv_mod = _import_server()
        with tempfile.TemporaryDirectory() as tmp:
            paths = srv_mod._collect_skill_search_paths(extra_paths=[tmp])
            assert paths[0] == tmp

    def test_dcc_mcp_maya_skill_paths_env_var(self):
        """DCC_MCP_MAYA_SKILL_PATHS (per-app) is honoured (v0.12.12+)."""
        import tempfile

        srv_mod = _import_server()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"DCC_MCP_MAYA_SKILL_PATHS": tmp}):
                paths = srv_mod._collect_skill_search_paths()
        assert tmp in paths

    def test_app_env_var_before_global_env_var(self):
        """Per-app env var (DCC_MCP_MAYA_SKILL_PATHS) appears before DCC_MCP_SKILL_PATHS."""
        import tempfile

        srv_mod = _import_server()
        with tempfile.TemporaryDirectory() as app_tmp, tempfile.TemporaryDirectory() as global_tmp:
            with patch.dict(
                "os.environ",
                {"DCC_MCP_MAYA_SKILL_PATHS": app_tmp, "DCC_MCP_SKILL_PATHS": global_tmp},
            ):
                paths = srv_mod._collect_skill_search_paths()
        assert app_tmp in paths
        assert global_tmp in paths
        assert paths.index(app_tmp) < paths.index(global_tmp)


class TestModuleSingleton:
    def test_start_stop_module_functions(self):
        """Module-level start_server / stop_server singleton pattern."""
        srv_mod = _import_server()
        handle = srv_mod.start_server(port=0, register_builtins=False)
        assert handle is not None
        srv_mod.stop_server()
        # After stop, the instance is reset
        assert srv_mod._server_instance is None

    def test_start_server_idempotent(self):
        """Calling start_server twice returns the same handle."""
        srv_mod = _import_server()
        h1 = srv_mod.start_server(port=0, register_builtins=False)
        h2 = srv_mod.start_server(port=0, register_builtins=False)
        assert h1 is h2
        srv_mod.stop_server()
