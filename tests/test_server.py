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


def _core_supports_nested_dcc_mcp_metadata():
    """True iff the installed dcc-mcp-core honours nested ``metadata.dcc-mcp``.

    After the sibling-file migration, every SKILL.md uses the nested
    mapping form (``metadata: { dcc-mcp: { tools: "tools.yaml", ... } }``).
    Cores older than dcc-mcp-core#385 silently drop these overrides,
    which makes the server-level assertions about ``__skill__`` stubs
    and group activation meaningless. We probe by scanning a temp skill
    and checking whether the override is actually applied.
    """
    import tempfile
    from pathlib import Path

    try:
        from dcc_mcp_core import scan_and_load
    except ImportError:
        return False

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe-skill"
        probe.mkdir()
        (probe / "tools.yaml").write_text(
            "tools:\n  - name: ping\n    description: probe tool\n",
            encoding="utf-8",
        )
        (probe / "SKILL.md").write_text(
            "---\n"
            "name: probe-skill\n"
            "description: probe for nested dcc-mcp metadata support\n"
            "metadata:\n"
            "  dcc-mcp:\n"
            "    dcc: maya\n"
            "    tools: tools.yaml\n"
            "---\n# body\n",
            encoding="utf-8",
        )
        try:
            skills, _ = scan_and_load(extra_paths=[tmp], dcc_name="maya")
        except Exception:
            return False
        for s in skills:
            if s.name == "probe-skill":
                tools = getattr(s, "tools", None)
                if callable(tools):
                    tools = tools()
                return bool(tools)
    return False


_CORE_SUPPORTS_NESTED_META = _core_supports_nested_dcc_mcp_metadata()

_skip_without_nested_meta = pytest.mark.skipif(
    not _CORE_SUPPORTS_NESTED_META,
    reason=(
        "Installed dcc-mcp-core does not support nested metadata.dcc-mcp "
        "(requires dcc-mcp-core#385 / >= 0.15). Skipping assertions that "
        "depend on skill tools/groups being visible to the scanner."
    ),
)

# The following Minimal-mode tests assert specific tool names and group
# structures that depend on a matching dcc-mcp-core release (>= 0.15).
# Pinning them to a version is brittle under CI matrices that resolve
# dcc-mcp-core from PyPI, so mark them xfail (strict=False) until a
# core release that ships the #385 fix and corresponding skill loader
# behaviour is cut. Once that's in requirements.txt as a floor, flip
# these back to strict assertions.
_xfail_minimal_loader_pending_core_release = pytest.mark.xfail(
    reason=(
        "Minimal-mode skill dispatch shape depends on dcc-mcp-core >= 0.15 "
        "(includes dcc-mcp-core#385). CI currently resolves an older core "
        "from PyPI."
    ),
    strict=False,
)


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
        """register_builtin_actions discovers skills into the SkillCatalog."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        # Pass explicit skills path to ensure discovery regardless of install mode
        server.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        # Verify skills are discovered via the SkillCatalog API (skills are lazy-loaded)
        discovered_skills = [s.name if hasattr(s, "name") else s["name"] for s in server._server.list_skills()]
        assert "maya-scripting" in discovered_skills
        assert "maya-scene" in discovered_skills
        assert "maya-render" in discovered_skills

    def test_mcp_url_none_when_not_running(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        assert server.mcp_url is None

    # ── Issue #136: attach_dispatcher wires the in-process executor ───────

    def test_attach_dispatcher_registers_core_host_dispatcher(self):
        """``attach_dispatcher`` must install the core 0.14.23 host path."""
        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        server._dcc_name = "maya"
        server._server = MagicMock()

        dispatcher = MagicMock(name="QueueDispatcher")
        with patch.object(server, "register_inprocess_executor", autospec=True) as mock_register:
            server.attach_dispatcher(dispatcher)

        server._server.attach_dispatcher.assert_called_once_with(dispatcher)
        assert mock_register.call_count == 1
        assert server._maya_dispatcher is dispatcher

    def test_detach_dispatcher_restores_inline_executor(self):
        """``attach_dispatcher(None)`` keeps the inline in-process executor active."""
        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        server._dcc_name = "maya"
        server._server = MagicMock()

        with patch.object(server, "register_inprocess_executor", autospec=True) as mock_register:
            server.attach_dispatcher(None)

        mock_register.assert_called_once_with(None)
        assert server._maya_dispatcher is None


# ── Issue #138: strict skill scan opt-in ──────────────────────────────────────


class TestStrictSkillScan:
    """Issue #138 — ``DCC_MCP_MAYA_STRICT_SKILL_SCAN=1`` surfaces skipped dirs."""

    def test_env_var_default_off(self, monkeypatch):
        from dcc_mcp_maya import _env

        monkeypatch.delenv(_env.ENV_STRICT_SKILL_SCAN, raising=False)
        assert _env.resolve_strict_skill_scan() is False

    def test_env_var_set_to_one_enables_strict(self, monkeypatch):
        from dcc_mcp_maya import _env

        monkeypatch.setenv(_env.ENV_STRICT_SKILL_SCAN, "1")
        assert _env.resolve_strict_skill_scan() is True

    def test_explicit_arg_overrides_env(self, monkeypatch):
        from dcc_mcp_maya import _env

        monkeypatch.setenv(_env.ENV_STRICT_SKILL_SCAN, "0")
        assert _env.resolve_strict_skill_scan(True) is True

    def test_strict_scan_raises_value_error_on_skipped_dirs(self, tmp_path):
        """When strict scan finds a malformed skill dir, startup must raise.

        Builds a fake skills directory containing an unparseable
        ``SKILL.md`` and asserts that ``register_builtin_actions(strict_scan=True)``
        propagates the ``ValueError`` from
        :func:`dcc_mcp_core.scan_and_load_strict`.
        """
        bad_skill = tmp_path / "bad-skill"
        bad_skill.mkdir()
        (bad_skill / "SKILL.md").write_text(
            "---\nthis is: not: valid: yaml: at: all\n---\n",
            encoding="utf-8",
        )

        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        try:
            with pytest.raises(ValueError):
                server.register_builtin_actions(
                    extra_skill_paths=[str(tmp_path)],
                    include_bundled=False,
                    strict_scan=True,
                )
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass


# ── Issue #139: workflow engine + job recovery propagation ───────────────────


class TestWorkflowEngineAndJobRecovery:
    """Issue #139 — wire upstream resume/retry/idempotency surface."""

    def test_workflows_disabled_by_default(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        try:
            assert server._config.enable_workflows is False
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_workflows_enabled_via_constructor_kwarg(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_workflows=True)
        try:
            assert server._config.enable_workflows is True
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_workflows_enabled_via_env_var(self, monkeypatch):
        from dcc_mcp_maya import _env

        monkeypatch.setenv(_env.ENV_ENABLE_WORKFLOWS, "1")
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        try:
            assert server._config.enable_workflows is True
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_job_recovery_default_drop_propagates(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        try:
            assert server._config.job_recovery == "drop"
            assert server._job_recovery == "drop"
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_job_recovery_requeue_propagates_to_inner_config(self, monkeypatch):
        """``DCC_MCP_MAYA_JOB_RECOVERY=requeue`` must reach ``_config.job_recovery``.

        Without the propagation added in this PR, the upstream Rust
        :class:`JobRecoveryPolicy` (dcc-mcp-core#567) defaulted to
        ``drop`` regardless of the env var, so interrupted idempotent
        jobs were never resumed on plugin restart (issue #139).
        """
        from dcc_mcp_maya import _env

        monkeypatch.setenv(_env.ENV_JOB_RECOVERY, "requeue")
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        try:
            assert server._job_recovery == "requeue"
            assert server._config.job_recovery == "requeue"
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass


class TestMayaMcpServerHttp:
    """End-to-end HTTP tests against a real McpHttpServer (no Maya needed)."""

    @pytest.fixture
    def running_server(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        # Pass explicit skills path to ensure discovery regardless of install mode
        server.register_builtin_actions(extra_skill_paths=[_builtin_skills_dir()])
        # Explicitly load key skills so their tools appear in tools/list
        for skill in ("maya-scripting", "maya-scene"):
            try:
                server._server.load_skill(skill)
            except Exception:
                pass
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
        # Core 0.14+ uses bare tool names (e.g. "create_sphere") when unique,
        # falling back to "<skill>.<action>" prefixed form on collisions.
        # Stub markers ("__skill__<name>") also carry the maya- prefix.
        # Verify that SOME skill-derived tools are present alongside the core
        # meta-tools — either as bare names, prefixed, or stub markers.
        skill_stubs = {n for n in names if n.startswith("__skill__maya-")}
        prefixed_tools = {n for n in names if n.startswith("maya-") and not n.startswith("__skill__")}
        # After the sibling-file migration (dcc-mcp-core #356/#385), skill
        # scripts are exposed with bare names when unique. We compute the
        # set of "skill-derived" tools by subtracting the known core
        # meta-tools and subsystem-prefixed tools (`jobs.*`, `diagnostics__*`).
        core_meta_tools = {
            "list_skills",
            "search_skills",  # replaces find_skills (renamed in dcc-mcp-core >= 0.14)
            "load_skill",
            "unload_skill",
            "search_tools",
            "get_skill_info",
            "activate_tool_group",
            "deactivate_tool_group",
            "list_roots",
        }
        reserved_prefix = ("__skill__", "jobs.", "diagnostics__", "ext.")
        bare_skill_tools = {
            n
            for n in names
            if n not in core_meta_tools and not n.startswith(reserved_prefix) and not n.startswith("maya-")
        }
        skill_tools = skill_stubs | prefixed_tools | bare_skill_tools
        assert len(skill_tools) >= 3, (
            f"Expected >=3 maya skill tools (stubs/prefixed/bare), got {len(skill_tools)}: {names}"
        )
        # Core meta-tools should always be present (find_skills removed in core >= 0.14)
        core_tools = {"list_skills", "search_skills", "load_skill", "unload_skill"}
        assert core_tools.issubset(names), f"Missing core meta-tools: {core_tools - names}"

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
    """collect_skill_search_paths respects all path sources."""

    def test_builtin_skills_always_included(self):
        from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR, MayaMcpServer

        srv = object.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        srv._builtin_skills_dir = _BUILTIN_SKILLS_DIR
        srv._handle = None
        srv._enable_gateway_failover = False
        srv._hot_reloader = None
        srv._gateway_election = None
        from dcc_mcp_core import McpHttpConfig

        srv._config = McpHttpConfig()
        srv._server = MagicMock()
        paths = srv.collect_skill_search_paths(include_bundled=False)
        assert str(_BUILTIN_SKILLS_DIR) in paths

    def test_extra_paths_take_highest_priority(self):
        import tempfile

        from dcc_mcp_maya.server import MayaMcpServer

        srv = object.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR

        srv._builtin_skills_dir = _BUILTIN_SKILLS_DIR
        srv._handle = None
        srv._enable_gateway_failover = False
        srv._hot_reloader = None
        srv._gateway_election = None
        from dcc_mcp_core import McpHttpConfig

        srv._config = McpHttpConfig()
        srv._server = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            paths = srv.collect_skill_search_paths(extra_paths=[tmp], include_bundled=False)
            assert paths[0] == tmp

    def test_dcc_mcp_maya_skill_paths_env_var(self):
        """DCC_MCP_MAYA_SKILL_PATHS (per-app) is honoured (v0.12.12+)."""
        import tempfile

        from dcc_mcp_maya.server import MayaMcpServer

        srv = object.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR

        srv._builtin_skills_dir = _BUILTIN_SKILLS_DIR
        srv._handle = None
        srv._enable_gateway_failover = False
        srv._hot_reloader = None
        srv._gateway_election = None
        from dcc_mcp_core import McpHttpConfig

        srv._config = McpHttpConfig()
        srv._server = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"DCC_MCP_MAYA_SKILL_PATHS": tmp}):
                paths = srv.collect_skill_search_paths(include_bundled=False)
        assert tmp in paths

    def test_app_env_var_before_global_env_var(self):
        """Per-app env var appears before DCC_MCP_SKILL_PATHS."""
        import tempfile

        from dcc_mcp_maya.server import MayaMcpServer

        srv = object.__new__(MayaMcpServer)
        srv._dcc_name = "maya"
        from dcc_mcp_maya.server import _BUILTIN_SKILLS_DIR

        srv._builtin_skills_dir = _BUILTIN_SKILLS_DIR
        srv._handle = None
        srv._enable_gateway_failover = False
        srv._hot_reloader = None
        srv._gateway_election = None
        from dcc_mcp_core import McpHttpConfig

        srv._config = McpHttpConfig()
        srv._server = MagicMock()
        with tempfile.TemporaryDirectory() as app_tmp, tempfile.TemporaryDirectory() as global_tmp:
            with patch.dict(
                "os.environ",
                {"DCC_MCP_MAYA_SKILL_PATHS": app_tmp, "DCC_MCP_SKILL_PATHS": global_tmp},
            ):
                paths = srv.collect_skill_search_paths(include_bundled=False)
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


class TestMinimalMode:
    """Tests for the minimal-mode default tool surface."""

    def test_minimal_default_loads_only_core_skills(self):
        """With minimal=True (default), only maya-scripting and maya-scene are loaded."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions(
            extra_skill_paths=[_builtin_skills_dir()],
            minimal=True,
        )
        # Check loaded skills via is_loaded
        assert server._server.is_loaded("maya-scripting")
        assert server._server.is_loaded("maya-scene")
        assert not server._server.is_loaded("maya-render")
        assert not server._server.is_loaded("maya-render-farm")
        server.stop()

    def test_minimal_default_registers_core_skill_handlers(self):
        """Minimal startup must wire newly-loaded core tools in-process.

        Regression for issue #136: without the post-load wiring pass,
        ``maya_scripting__execute_python`` is visible but has no Python handler,
        so the core falls back to subprocess execution (mayapy).
        """
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        try:
            server.register_builtin_actions(
                extra_skill_paths=[_builtin_skills_dir()],
                minimal=True,
            )

            assert getattr(server, "_inprocess_executor_registered", False)
        finally:
            server.stop()

    def test_minimal_false_loads_all_skills(self):
        """With minimal=False, all discovered skills are loaded (legacy behaviour)."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions(
            extra_skill_paths=[_builtin_skills_dir()],
            minimal=False,
        )
        # All 12 bundled skills should be loaded in legacy mode
        assert server._server.loaded_count() >= 10
        assert server._server.is_loaded("maya-scripting")
        assert server._server.is_loaded("maya-scene")
        assert server._server.is_loaded("maya-render")
        server.stop()

    def test_minimal_env_override(self):
        """DCC_MCP_MAYA_MINIMAL=0 forces legacy full-load behaviour."""
        srv_mod = _import_server()
        with patch.dict("os.environ", {"DCC_MCP_MAYA_MINIMAL": "0"}):
            server = srv_mod.MayaMcpServer(port=0)
            server.register_builtin_actions(
                extra_skill_paths=[_builtin_skills_dir()],
                minimal=None,  # let env var decide
            )
            assert server._server.loaded_count() >= 10
            server.stop()

    @_xfail_minimal_loader_pending_core_release
    def test_minimal_tools_list_has_core_tools(self):
        """In minimal mode, tools/list contains execute_python and get_scene_info."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions(
            extra_skill_paths=[_builtin_skills_dir()],
            minimal=True,
        )
        handle = server.start()
        # Fetch tools/list
        data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
        req = urllib.request.Request(
            handle.mcp_url(),
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())
        names = {t["name"] for t in body["result"]["tools"]}
        # Core meta-tools
        assert "load_skill" in names
        assert "list_skills" in names
        # Core skill tools (execute_python, get_scene_info should be present)
        has_execute_python = any("execute_python" in n for n in names)
        has_get_scene_info = any("get_scene_info" in n for n in names)
        assert has_execute_python, f"execute_python not found in tools: {names}"
        assert has_get_scene_info, f"get_scene_info not found in tools: {names}"
        # Non-core skills should be stubs
        skill_stubs = [n for n in names if n.startswith("__skill__")]
        assert len(skill_stubs) > 0, "Expected __skill__ stubs for unloaded skills"
        # Extended/scene-management groups should be deactivated
        # (their tools should NOT appear as full tools)
        has_mesh_ops = any("mesh_ops" in n for n in names)
        has_new_scene = any("new_scene" in n for n in names)
        assert not has_mesh_ops, f"mesh_ops (extended group) should be deactivated: {names}"
        assert not has_new_scene, f"new_scene (scene-management group) should be deactivated: {names}"
        server.stop()

    @_xfail_minimal_loader_pending_core_release
    def test_minimal_deactivates_extended_groups(self):
        """In minimal mode, extended groups are deactivated within loaded skills."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions(
            extra_skill_paths=[_builtin_skills_dir()],
            minimal=True,
        )
        # Check that the registry has the groups but they're disabled
        registry = server._server.registry
        groups = registry.list_groups()
        assert "extended" in groups
        assert "scene-management" in groups
        assert "core" in groups
        server.stop()

    def test_custom_default_tools_env(self):
        """DCC_MCP_MAYA_DEFAULT_TOOLS customises which skills are loaded."""
        srv_mod = _import_server()
        with patch.dict("os.environ", {"DCC_MCP_MAYA_DEFAULT_TOOLS": "maya-scripting,maya-render"}):
            server = srv_mod.MayaMcpServer(port=0)
            server.register_builtin_actions(
                extra_skill_paths=[_builtin_skills_dir()],
                minimal=True,
            )
            assert server._server.is_loaded("maya-scripting")
            assert server._server.is_loaded("maya-render")
            # maya-scene was NOT in the custom list
            assert not server._server.is_loaded("maya-scene")
            server.stop()
