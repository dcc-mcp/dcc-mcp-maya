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
import threading
import types
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


class TestPluginStartupMode:
    def test_interactive_initialize_starts_on_main_thread(self, plugin_module, mock_maya_modules):
        mock_maya_modules.cmds.about.side_effect = lambda **kwargs: False if kwargs.get("batch") else "2025"
        plugin_module._add_menu = MagicMock()
        plugin_module._start_async = MagicMock()
        plugin_module._start = MagicMock()

        plugin_module.initializePlugin(MagicMock())

        plugin_module._add_menu.assert_called_once_with()
        plugin_module._start_async.assert_called_once_with()
        plugin_module._start.assert_not_called()

    def test_batch_initialize_starts_synchronously(self, plugin_module, mock_maya_modules):
        mock_maya_modules.cmds.about.side_effect = lambda **kwargs: True if kwargs.get("batch") else "2025"
        plugin_module._start_async = MagicMock()
        plugin_module._start = MagicMock()

        plugin_module.initializePlugin(MagicMock())

        plugin_module._start.assert_called_once_with()
        plugin_module._start_async.assert_not_called()


class TestStartAsyncSchedulesFinalisation:
    """Regression: ``_start_async`` must defer the synchronous ``_start``
    path to Maya's main-thread post-boot idle moment via
    ``cmds.evalDeferred(_start, lowestPriority=True)`` — and MUST NOT use
    any of the previously-attempted cross-thread coordination patterns.

    History — every blocked variant is regression-locked below
    -----------------------------------------------------------
    1. ``cmds.evalDeferred(_finish, lowestPriority=True)`` from a worker
       thread crashed with::

           必须为标志"lowestPriority"传递一个布尔参数

       because ``cmds.*`` is not thread-safe — kwargs are marshalled
       through the MEL command engine on the wrong thread.

    2. ``maya.utils.executeDeferred(_finish)`` from a worker thread was
       thread-safe in theory but **deadlocked** Maya in 2022/2023 builds:
       it routes through ``executeInMainThreadWithResult`` whose channel
       is gated on a flag flipped only after plugin-init completes, so
       the worker (holding the GIL) and the main thread (inside
       ``initializePlugin``, waiting on the worker via the GIL) form a
       cycle that pins Maya forever.

    3. ``cmds.scriptJob(idleEvent=poll, protected=True)`` + a
       ``threading.Event`` polled from the worker still raced against
       Maya's plugin-init re-entrancy guards in some builds.

    The current design (per user request 2026-05-13): wait for Maya's
    main-thread boot to finish via ``cmds.evalDeferred(_start,
    lowestPriority=True)`` (called from the main thread inside
    ``initializePlugin`` — safe), then run the synchronous ``_start``
    path in-place. No worker thread, no scriptJob, no event coordination.
    """

    def _install_core_stubs(self) -> dict:
        """Inject minimal ``dcc_mcp_core.host`` + ``dcc_mcp_maya`` stubs into
        ``sys.modules`` so the plugin's lazy imports inside ``_start``
        resolve without pulling the real dependency graph."""

        host_mod = types.ModuleType("dcc_mcp_core.host")
        host_mod.QueueDispatcher = MagicMock(name="QueueDispatcher")
        host_mod.BlockingDispatcher = MagicMock(name="BlockingDispatcher")

        core_mod = types.ModuleType("dcc_mcp_core")
        core_mod.host = host_mod

        dcc_mod = types.ModuleType("dcc_mcp_maya")
        dcc_mod.start_server = MagicMock(name="start_server", return_value=MagicMock())
        dcc_mod.MayaHost = MagicMock(name="MayaHost")

        return {
            "dcc_mcp_core": core_mod,
            "dcc_mcp_core.host": host_mod,
            "dcc_mcp_maya": dcc_mod,
        }

    def test_start_async_only_calls_evalDeferred_with_lowest_priority(self, plugin_module, mock_maya_modules):
        """``_start_async`` must hand Maya exactly one deferred callback,
        scheduled with ``lowestPriority=True`` so it fires after every other
        boot-time deferred task in the queue.

        ``lowestPriority=True`` is critical: without it the callback fires
        at the *front* of the deferred queue, before ``userSetup.py`` follow-
        ups, autoload scene, and other plugins' init code complete — i.e.
        while Maya is still half-initialised, exactly the state in which
        every previous cross-thread variant deadlocked.
        """

        plugin_module._start = MagicMock()
        plugin_module._start_async()

        evalDeferred = mock_maya_modules.cmds.evalDeferred
        evalDeferred.assert_called_once()
        args, kwargs = evalDeferred.call_args
        # First positional arg is the callable to defer.
        assert args, "evalDeferred must receive a callable (positional arg)"
        assert callable(args[0]), f"first arg must be callable, got {type(args[0])!r}"
        assert args[0] is plugin_module._start, (
            "the deferred callable must be _start (the synchronous main-thread "
            "startup path), not a closure that re-introduces async coordination"
        )
        assert kwargs.get("lowestPriority") is True, (
            "lowestPriority=True is required so the callback fires at the BACK "
            "of Maya's deferred queue (after userSetup.py / autoload scene / "
            "other plugins' init complete)"
        )

    def test_start_async_does_not_spawn_worker_thread(self, plugin_module, mock_maya_modules):
        """Regression: no worker thread may be spawned. Every previous
        worker-based variant deadlocked Maya during plugin init."""

        plugin_module._start = MagicMock()
        threads_before = {t.ident for t in threading.enumerate()}
        plugin_module._start_async()
        threads_after = {t.ident for t in threading.enumerate()}

        new_threads = threads_after - threads_before
        assert not new_threads, (
            f"_start_async must not spawn any thread, but {len(new_threads)} appeared: {new_threads!r}"
        )

    def test_start_async_does_not_use_executeDeferred_or_scriptJob(self, plugin_module, mock_maya_modules):
        """Regression: ``maya.utils.executeDeferred`` and
        ``cmds.scriptJob(idleEvent=...)`` are forbidden in the startup path
        — both have been observed to deadlock or race during plugin init.
        Only ``cmds.evalDeferred(callable, lowestPriority=True)`` from the
        main thread is allowed (validated in the sibling test)."""

        plugin_module._start = MagicMock()
        plugin_module._start_async()

        mock_maya_modules.utils.executeDeferred.assert_not_called()

        scriptjob = mock_maya_modules.cmds.scriptJob
        idle_event_calls = [call for call in scriptjob.call_args_list if "idleEvent" in call.kwargs]
        assert not idle_event_calls, (
            f"_start_async must NOT register an idleEvent scriptJob, but found "
            f"{len(idle_event_calls)}: {idle_event_calls!r}"
        )

    def test_deferred_callable_invokes_start_synchronously(self, plugin_module, mock_maya_modules):
        """When Maya finally fires the deferred callback (at the back of the
        queue, post-boot), it must run ``_start`` synchronously on the
        calling (main) thread — no further deferral, no worker thread."""

        plugin_module._start = MagicMock()
        plugin_module._start_async()

        args, _kwargs = mock_maya_modules.cmds.evalDeferred.call_args
        deferred_callable = args[0]

        # Simulate Maya firing the deferred callback on the main thread.
        deferred_callable()

        plugin_module._start.assert_called_once_with()


class TestSidecarSharesRegistryWithInProcessServer:
    """Regression: ``_maybe_spawn_sidecar`` MUST pass ``registry_dir`` to
    ``start_sidecar`` so the sidecar joins the same FileRegistry as the
    in-process MCP server.

    The previous default behaviour split-brained the registry:

    * ``dcc-mcp-server sidecar`` (Rust crate ``dcc-mcp-server::sidecar``)
      defaulted to ``%TEMP%\\dcc-mcp\\registry\\``.
    * ``DccServerBase`` / ``GatewayRunner`` defaulted to
      ``%TEMP%\\dcc-mcp-registry\\``.

    Two registries that never see each other -> gateway election cannot
    arbitrate across in-process and sidecar candidates -> 9765 stays
    dark. RFC #998 follow-up (2026-05-16 three-Maya live session: 36
    stale sidecar rows accumulated in the wrong dir, gateway port had
    no listener despite all processes alive).
    """

    def _arm_plugin(self, plugin_module, monkeypatch):
        """Stub ``dcc_mcp_maya.sidecar`` so ``_maybe_spawn_sidecar`` resolves
        and calls our mock ``start_sidecar``."""

        plugin_module._sidecar_handle = None
        import dcc_mcp_maya.sidecar as sidecar_pkg

        monkeypatch.setattr(sidecar_pkg, "is_sidecar_mode_enabled", lambda: True)
        monkeypatch.setattr(sidecar_pkg, "start_sidecar", MagicMock(name="start_sidecar", return_value=MagicMock()))
        monkeypatch.setattr(sidecar_pkg, "stop_sidecar", MagicMock(name="stop_sidecar"))

        # Stub the banner so we don't print to stdout during tests.
        plugin_module._print_sidecar_info = MagicMock()
        return sidecar_pkg

    def test_sidecar_inherits_DCC_MCP_REGISTRY_DIR_env(self, plugin_module, monkeypatch, tmp_path):
        """When ``DCC_MCP_REGISTRY_DIR`` is set the sidecar must use it."""
        custom_dir = tmp_path / "custom-registry"
        monkeypatch.setenv("DCC_MCP_REGISTRY_DIR", str(custom_dir))

        sidecar_pkg = self._arm_plugin(plugin_module, monkeypatch)
        plugin_module._maybe_spawn_sidecar()

        sidecar_pkg.start_sidecar.assert_called_once()
        _, kwargs = sidecar_pkg.start_sidecar.call_args
        assert "registry_dir" in kwargs, "start_sidecar must receive registry_dir to keep registries unified"
        assert str(kwargs["registry_dir"]) == str(custom_dir)

    def test_sidecar_mode_disables_in_process_gateway_port(self, plugin_module, monkeypatch):
        """Gateway election must run in the sidecar binary, not in Maya's PyO3 server."""
        monkeypatch.setenv("DCC_MCP_MAYA_SIDECAR", "1")
        monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "9765")
        cfg = plugin_module._resolve_config()
        assert cfg.get("gateway_port") is None or cfg.get("gateway_port") == 0

    def test_sidecar_defaults_to_maya_gateway_registry_path(self, plugin_module, monkeypatch, tmp_path):
        """When ``DCC_MCP_REGISTRY_DIR`` is unset, the sidecar must default
        to the SAME path the in-process ``GatewayRunner`` uses, namely
        ``<tempdir>/dcc-mcp-registry``. NOT ``<tempdir>/dcc-mcp/registry``
        (the Rust sidecar binary's own default, which would split-brain
        the registry)."""
        # Pin tempdir to a known location so we can assert the path shape.
        monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
        monkeypatch.delenv("DCC_MCP_REGISTRY_DIR", raising=False)

        sidecar_pkg = self._arm_plugin(plugin_module, monkeypatch)
        plugin_module._maybe_spawn_sidecar()

        _, kwargs = sidecar_pkg.start_sidecar.call_args
        chosen = Path(kwargs["registry_dir"])
        expected = tmp_path / "dcc-mcp-registry"
        assert chosen == expected, (
            f"sidecar registry_dir must be {expected} (matches GatewayRunner "
            f"default), got {chosen}. The Rust sidecar binary's default "
            f"({tmp_path / 'dcc-mcp' / 'registry'}) is the wrong path and "
            f"splits the registry."
        )


class TestRestartStopsSidecar:
    """Restart MCP Server must tear down the prior sidecar before respawning."""

    def test_stop_sidecar_if_running_clears_handle(self, plugin_module, monkeypatch):
        sidecar_pkg = TestSidecarSharesRegistryWithInProcessServer()._arm_plugin(plugin_module, monkeypatch)
        mock_handle = MagicMock()
        plugin_module._sidecar_handle = mock_handle

        plugin_module._stop_sidecar_if_running()

        sidecar_pkg.stop_sidecar.assert_called_once_with(mock_handle)
        assert plugin_module._sidecar_handle is None

    def test_stop_sidecar_if_running_is_noop_when_absent(self, plugin_module, monkeypatch):
        sidecar_pkg = TestSidecarSharesRegistryWithInProcessServer()._arm_plugin(plugin_module, monkeypatch)
        sidecar_pkg.stop_sidecar = MagicMock(name="stop_sidecar")
        plugin_module._sidecar_handle = None

        plugin_module._stop_sidecar_if_running()

        sidecar_pkg.stop_sidecar.assert_not_called()

    def test_restart_deferred_stops_sidecar_before_respawn(self, plugin_module, monkeypatch, mock_maya_modules):
        sidecar_pkg = TestSidecarSharesRegistryWithInProcessServer()._arm_plugin(plugin_module, monkeypatch)
        mock_handle = MagicMock()
        plugin_module._sidecar_handle = mock_handle
        plugin_module._stop_host_on_main_thread = MagicMock()
        plugin_module._start = MagicMock()

        if plugin_module._restart_lock.locked():
            plugin_module._restart_lock.release()

        import dcc_mcp_maya

        dcc_mcp_maya.stop_server = MagicMock()

        def _run_thread_immediately(target, daemon=True, name=None):  # noqa: ARG001
            target()
            return MagicMock()

        def _run_deferred(fn):
            fn()

        monkeypatch.setattr("threading.Thread", _run_thread_immediately)
        mock_maya_modules.utils.executeDeferred = _run_deferred

        plugin_module._restart_deferred()

        sidecar_pkg.stop_sidecar.assert_called_once_with(mock_handle)
        assert plugin_module._sidecar_handle is None
        plugin_module._start.assert_called_once_with()


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
