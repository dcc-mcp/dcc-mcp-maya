"""Tests for MayaMcpServer (no real Maya required — maya.cmds is mocked)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import io
import json
import logging
import sys
import types
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


def test_dispatcher_shutdown_log_normalizes_missing_count(caplog):
    srv_mod = _import_server()

    with caplog.at_level(logging.INFO, logger=srv_mod.logger.name):
        srv_mod._log_dispatcher_shutdown("maya", None)

    assert "dispatcher.shutdown signalled 0 job(s)" in caplog.text


def test_dispatcher_shutdown_log_skips_closed_stream(capsys):
    srv_mod = _import_server()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    srv_mod.logger.addHandler(handler)
    try:
        stream.close()

        srv_mod._log_dispatcher_shutdown("maya", None)

        assert capsys.readouterr().err == ""
    finally:
        srv_mod.logger.removeHandler(handler)


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


def _builtin_skills_dir():
    """Return the built-in skills directory, resolving it from the package."""
    from pathlib import Path

    import dcc_mcp_maya

    return str(Path(dcc_mcp_maya.__file__).parent / "skills")


def _mcp_post_json(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


def _list_all_mcp_tools(url):
    """Walk core 0.15.9+ ``tools/list`` cursor pages and return every tool."""
    tools = []
    cursor = None
    pages = 0
    while True:
        body = {"jsonrpc": "2.0", "id": pages + 1, "method": "tools/list"}
        if cursor:
            body["params"] = {"cursor": cursor}
        code, response = _mcp_post_json(url, body)
        assert code == 200
        result = response.get("result", {})
        tools.extend(result.get("tools", []))
        cursor = result.get("nextCursor")
        if not cursor:
            return tools
        pages += 1
        if pages > 50:
            raise RuntimeError("tools/list pagination exceeded 50 pages")


# ── MayaMcpServer unit tests ──────────────────────────────────────────────────


class TestMayaMcpServerApi:
    def test_explicit_gateway_port_zero_disables_gateway(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, gateway_port=0)
        assert server._config.gateway_port == 0
        server.stop()

    def test_gateway_failover_false_disables_default_gateway(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_gateway_failover=False)
        assert server._config.gateway_port == 0
        server.stop()

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

    # ── Issue #136: attach_dispatcher wires the host execution bridge ─────

    def test_attach_dispatcher_registers_core_host_dispatcher(self):
        """``attach_dispatcher`` must install the core HostExecutionBridge path."""
        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        server._dcc_name = "maya"
        server._config = MagicMock(sandbox_policy=None)
        server._server = MagicMock()
        # Readiness binder is created in ``__init__``; bypassing it
        # means we must supply a stand-in so ``attach_dispatcher`` can
        # re-bind without crashing.
        server._readiness = MagicMock()

        dispatcher = MagicMock(name="QueueDispatcher")
        with patch.object(server, "register_host_execution_bridge", autospec=True) as mock_register:
            server.attach_dispatcher(dispatcher)

        server._server.attach_dispatcher.assert_called_once_with(dispatcher)
        assert mock_register.call_count == 1
        assert server._execution_bridge.runner is srv_mod._executor.run_skill_script
        assert server._maya_dispatcher is dispatcher

    def test_detach_dispatcher_restores_inline_executor(self):
        """``attach_dispatcher(None)`` keeps the inline host execution bridge active."""
        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        server._dcc_name = "maya"
        server._server = MagicMock()
        server._readiness = MagicMock()

        with patch.object(server, "register_host_execution_bridge", autospec=True) as mock_register:
            server.attach_dispatcher(None)

        assert mock_register.call_count == 1
        assert server._execution_bridge.dispatcher is None
        assert server._maya_dispatcher is None

    def test_default_standalone_dispatcher_detects_mayapy_executable(self, monkeypatch):
        """mayapy may report ``about(batch=True) == False`` after standalone init."""
        srv_mod = _import_server()
        maya_mod = types.ModuleType("maya")
        maya_mod.__path__ = []
        cmds_mod = types.ModuleType("maya.cmds")
        standalone_mod = types.ModuleType("maya.standalone")
        cmds_mod.about = MagicMock(return_value=False)
        maya_mod.cmds = cmds_mod
        maya_mod.standalone = standalone_mod

        monkeypatch.setattr(sys, "executable", "/usr/autodesk/maya2022/bin/python-bin")
        with patch.dict(
            sys.modules,
            {
                "maya": maya_mod,
                "maya.cmds": cmds_mod,
                "maya.standalone": standalone_mod,
            },
        ):
            dispatcher = srv_mod.MayaMcpServer._default_standalone_dispatcher()

        assert dispatcher is not None
        assert type(dispatcher).__name__ == "MayaStandaloneDispatcher"

    def test_constructor_installs_ui_dispatcher_for_gui_start_server(self):
        """Direct GUI ``start_server()`` needs a main-thread dispatcher by default."""
        srv_mod = _import_server()
        maya_mod = types.ModuleType("maya")
        maya_mod.__path__ = []
        cmds_mod = types.ModuleType("maya.cmds")
        cmds_mod.about = MagicMock(return_value=False)
        cmds_mod.scriptJob = MagicMock(return_value=42)
        maya_mod.cmds = cmds_mod

        with patch.dict(
            sys.modules,
            {
                "maya": maya_mod,
                "maya.cmds": cmds_mod,
            },
        ):
            server = srv_mod.MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
            try:
                assert type(server._maya_dispatcher).__name__ == "MayaUiDispatcher"
                assert server._auto_ui_pump is not None
                assert server._auto_ui_pump.is_installed is True
            finally:
                server.stop()

        assert server._auto_ui_pump is None

    def test_default_host_dispatcher_reuses_standalone_dispatcher(self):
        """Batch / mayapy keeps the serialized standalone dispatcher path."""
        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        standalone = object()

        with patch.object(srv_mod.MayaMcpServer, "_default_standalone_dispatcher", return_value=standalone):
            assert server._default_host_dispatcher() is standalone

    def test_default_host_dispatcher_returns_none_when_maya_probe_fails(self):
        """If Maya cannot answer ``about(batch=True)``, keep the inline path."""
        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        cmds_mod = sys.modules["maya.cmds"]
        cmds_mod.about.side_effect = RuntimeError("maya unavailable")

        with patch.object(srv_mod.MayaMcpServer, "_default_standalone_dispatcher", return_value=None):
            assert server._default_host_dispatcher() is None

    def test_default_host_dispatcher_returns_none_for_batch_maya(self):
        """Batch Maya without the standalone detector does not need a UI pump."""
        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        cmds_mod = sys.modules["maya.cmds"]
        cmds_mod.about.return_value = True

        with patch.object(srv_mod.MayaMcpServer, "_default_standalone_dispatcher", return_value=None):
            assert server._default_host_dispatcher() is None

    def test_default_host_dispatcher_returns_none_when_ui_dispatcher_import_fails(self):
        """Import failures fall back to the historical inline executor."""
        import builtins

        srv_mod = _import_server()
        server = object.__new__(srv_mod.MayaMcpServer)
        server._dcc_name = "maya"
        cmds_mod = sys.modules["maya.cmds"]
        cmds_mod.about.return_value = False
        real_import = builtins.__import__

        def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "dcc_mcp_maya.dispatcher":
                raise ImportError("blocked for test")
            return real_import(name, globals, locals, fromlist, level)

        with patch.object(srv_mod.MayaMcpServer, "_default_standalone_dispatcher", return_value=None):
            with patch.object(builtins, "__import__", side_effect=blocked_import):
                assert server._default_host_dispatcher() is None

    def test_default_host_dispatcher_keeps_dispatcher_when_pump_install_raises(self):
        """A pump-install failure should not prevent dispatcher wiring."""
        srv_mod = _import_server()
        import dcc_mcp_maya.dispatcher as dispatcher_mod

        server = object.__new__(srv_mod.MayaMcpServer)
        server._dcc_name = "maya"
        server._auto_ui_pump = None
        cmds_mod = sys.modules["maya.cmds"]
        cmds_mod.about.return_value = False

        class FailingPump:
            def __init__(self, dispatcher):
                self.dispatcher = dispatcher

            def install(self):
                raise RuntimeError("no idle pump")

        with patch.object(srv_mod.MayaMcpServer, "_default_standalone_dispatcher", return_value=None):
            with patch.object(dispatcher_mod, "MayaUiPump", FailingPump):
                dispatcher = server._default_host_dispatcher()

        assert type(dispatcher).__name__ == "MayaUiDispatcher"
        assert isinstance(server._auto_ui_pump, FailingPump)

    def test_standalone_affinity_override_uses_core_skill_object(self):
        """mayapy direct HTTP adjusts detached core skill metadata before loading."""
        srv_mod = _import_server()

        class Tool:
            def __init__(self, enforce_thread_affinity):
                self.enforce_thread_affinity = enforce_thread_affinity

        class Skill:
            def __init__(self):
                self.tools = [Tool(True), Tool(False)]

        class Inner:
            def __init__(self):
                self.skill = Skill()
                self.loaded = None

            def get_skill(self, name):
                assert name == "maya-scene"
                return self.skill

            def load_skill_object(self, skill):
                self.loaded = skill

            def load_skill(self, name):  # pragma: no cover - must not be used
                raise AssertionError(f"unexpected YAML-backed load_skill({name!r})")

        server = object.__new__(srv_mod.MayaMcpServer)
        server._dcc_name = "maya"
        server._host_dispatcher = type("MayaStandaloneDispatcher", (), {})()
        server._server = Inner()
        server._skill_client = MagicMock()
        server._skill_client.get_skill.side_effect = server._server.get_skill
        server._skill_client.load_skill_object.side_effect = server._server.load_skill_object

        assert server._load_skill_via_core_object("maya-scene") is True
        assert server._server.loaded is server._server.skill
        server._skill_client.get_skill.assert_called_once_with("maya-scene")
        server._skill_client.load_skill_object.assert_called_once_with(server._server.skill)
        assert [tool.enforce_thread_affinity for tool in server._server.skill.tools] == [False, False]

    def test_standalone_affinity_prepare_persists_for_core_catalog_load(self):
        """Core-owned MCP load_skill sees Maya standalone metadata overrides too."""
        srv_mod = _import_server()

        dispatcher = type("MayaStandaloneDispatcher", (), {})()
        server = srv_mod.MayaMcpServer(
            port=0,
            enable_gateway_failover=False,
            gateway_port=0,
            host_dispatcher=dispatcher,
        )
        try:
            server.register_builtin_actions(minimal=True)
            loaded = server._server.load_skill("maya-primitives")
            assert "maya_primitives__create_sphere" in loaded
            meta = server._server.registry.get_action("maya_primitives__create_sphere")
            assert meta is not None
            assert meta["thread_affinity"] == "main"
            assert meta.get("enforce_thread_affinity", False) is False
        finally:
            server.stop()

    def test_standalone_registration_discovers_bundled_skills_without_pyyaml(self):
        """Clean release archives do not need PyYAML to expose Maya skills."""
        srv_mod = _import_server()
        dispatcher = type("MayaStandaloneDispatcher", (), {})()

        with patch.dict(sys.modules, {"yaml": None}):
            server = srv_mod.MayaMcpServer(
                port=0,
                enable_gateway_failover=False,
                gateway_port=0,
                host_dispatcher=dispatcher,
            )
            try:
                server.register_builtin_actions(minimal=True)
                assert server._registration_report.outcomes[0].success is True
                skills = server.list_skills()
                assert any(skill.get("name") == "maya-scene" for skill in skills)
                assert server.load_skill("maya-scene") is True
                assert any("maya_scene__get_session_info" in str(action) for action in server.list_actions())
            finally:
                server.stop()

    def test_affinity_override_skipped_for_host_dispatcher(self):
        """Only standalone dispatchers need object-level affinity overrides."""
        srv_mod = _import_server()

        server = srv_mod.MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
        server._host_dispatcher = object()
        try:
            assert server._uses_standalone_affinity_override() is False
        finally:
            server.stop()


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
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
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
        names = {t["name"] for t in _list_all_mcp_tools(handle.mcp_url())}
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

    def test_minimal_false_discovers_without_eager_loading(self):
        """With minimal=False, core discovers skills without applying minimal eager loading."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions(
            extra_skill_paths=[_builtin_skills_dir()],
            minimal=False,
        )
        assert server._server.loaded_count() == 0
        assert not server._server.is_loaded("maya-scripting")
        assert not server._server.is_loaded("maya-scene")
        server.stop()

    def test_minimal_env_override_disables_eager_loading(self):
        """DCC_MCP_MINIMAL=0 disables core's declarative minimal-mode config."""
        srv_mod = _import_server()
        with patch.dict("os.environ", {"DCC_MCP_MINIMAL": "0"}):
            server = srv_mod.MayaMcpServer(port=0)
            server.register_builtin_actions(
                extra_skill_paths=[_builtin_skills_dir()],
                minimal=None,
            )
            assert server._server.loaded_count() == 0
            server.stop()

    def test_minimal_tools_list_has_core_tools(self):
        """In minimal mode, tools/list contains execute_python and get_scene_info."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions(
            extra_skill_paths=[_builtin_skills_dir()],
            minimal=True,
        )
        handle = server.start()
        names = {t["name"] for t in _list_all_mcp_tools(handle.mcp_url())}
        # Core meta-tools
        assert "load_skill" in names
        assert "list_skills" in names
        # Core skill tools (execute_python, get_scene_info should be present)
        has_execute_python = any("execute_python" in n for n in names)
        has_get_scene_info = any("get_scene_info" in n for n in names)
        assert has_execute_python, f"execute_python not found in tools: {names}"
        assert has_get_scene_info, f"get_scene_info not found in tools: {names}"
        # Latest core pages the complete ``tools/list`` surface and may include
        # progressive-loading stubs plus currently visible non-core actions.
        # This test only owns the minimal-mode guarantee that core tools are
        # discoverable across all pages; group activation is covered separately.
        server.stop()

    def test_minimal_deactivates_extended_groups(self):
        """In minimal mode, extended groups are deactivated within loaded skills."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.register_builtin_actions(
            extra_skill_paths=[_builtin_skills_dir()],
            minimal=True,
        )
        registry = server._server.registry
        groups = registry.list_groups()
        assert "core" in groups
        assert "scene-management" in groups
        assert "extended" not in groups
        server.stop()

    def test_custom_default_tools_env(self):
        """DCC_MCP_DEFAULT_TOOLS customises which skills are loaded."""
        srv_mod = _import_server()
        with patch.dict("os.environ", {"DCC_MCP_DEFAULT_TOOLS": "maya-scripting,maya-render"}):
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
