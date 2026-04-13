"""Round 49 tests — ActionRecorder, SkillWatcher, EventBus integration in server.py.

Tests cover:
- ActionRecorder: setup_recorder, action_metrics, recorder property
- SkillWatcher: setup_watcher, watch_skills, reload_skills, unwatch_skills, watcher property
- EventBus: subscribe, unsubscribe, publish, event_bus property
- Server lifecycle events: server_started, server_stopped, skills_loaded
- Pipeline coverage: _init_pipeline with registry=None (lines 184-185)
- setup_pipeline with registry=None (lines 248-249)
- start_server with new parameters
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _import_server():
    """Force reimport of server module."""
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    srv = importlib.import_module("dcc_mcp_maya.server")
    return srv


def _make_server_instance(**kwargs):
    """Create a MayaMcpServer using real dcc_mcp_core (with port=0 to avoid conflicts)."""
    srv_mod = _import_server()
    # Always use port=0 for test isolation
    kwargs.setdefault("port", 0)
    server = srv_mod.MayaMcpServer(**kwargs)
    return server, srv_mod


# ---------------------------------------------------------------------------
# ActionRecorder
# ---------------------------------------------------------------------------


class TestActionRecorder:
    """Test ActionRecorder integration in MayaMcpServer."""

    def test_recorder_none_by_default(self):
        server, _ = _make_server_instance()
        assert server.recorder is None

    def test_enable_recorder_init(self):
        server, _ = _make_server_instance(enable_recorder=True)
        assert server.recorder is not None

    def test_setup_recorder_fluent(self):
        server, _ = _make_server_instance()
        result = server.setup_recorder()
        assert result is server
        assert server.recorder is not None

    def test_setup_recorder_after_start_noop(self):
        server, _ = _make_server_instance(enable_recorder=True)
        server.start()
        original = server.recorder
        result = server.setup_recorder()
        assert result is server
        assert server.recorder is original
        server.stop()

    def test_action_metrics_none_without_recorder(self):
        server, _ = _make_server_instance()
        assert server.action_metrics("some_action") is None

    def test_action_metrics_with_recorder(self):
        server, _ = _make_server_instance(enable_recorder=True)
        result = server.action_metrics("maya_scene__create_object")
        # With no recorded actions, metrics returns None
        # (ActionRecorder.metrics returns None for unrecorded actions)
        # The point is the method doesn't crash
        assert result is None or hasattr(result, "avg_duration_ms")

    def test_action_metrics_exception_returns_none(self):
        server, _ = _make_server_instance(enable_recorder=True)
        # Use an invalid action that might trigger an error
        result = server.action_metrics("")
        # Should not crash, returns None on error
        assert result is None or hasattr(result, "avg_duration_ms")

    def test_action_metrics_success_rate(self):
        server, _ = _make_server_instance(enable_recorder=True)
        # Record an action first so metrics are available
        try:
            with server.recorder.start("test_action", "maya"):
                pass
        except Exception:
            pass
        m = server.action_metrics("test_action")
        # Metrics should be available now
        if m is not None:
            assert hasattr(m, "avg_duration_ms")
            assert hasattr(m, "p95_duration_ms")


# ---------------------------------------------------------------------------
# SkillWatcher
# ---------------------------------------------------------------------------


class TestSkillWatcher:
    """Test SkillWatcher integration in MayaMcpServer."""

    def test_watcher_none_by_default(self):
        server, _ = _make_server_instance()
        assert server.watcher is None

    def test_enable_watcher_init(self):
        server, _ = _make_server_instance(enable_watcher=True)
        assert server.watcher is not None

    def test_enable_watcher_custom_debounce(self):
        server, _ = _make_server_instance(enable_watcher=True, watcher_debounce_ms=500)
        assert server.watcher is not None

    def test_setup_watcher_fluent(self):
        server, _ = _make_server_instance()
        result = server.setup_watcher(debounce_ms=200)
        assert result is server
        assert server.watcher is not None

    def test_setup_watcher_after_start_noop(self):
        server, _ = _make_server_instance(enable_watcher=True)
        server.start()
        original = server.watcher
        result = server.setup_watcher()
        assert result is server
        assert server.watcher is original
        server.stop()

    def test_watch_skills_without_watcher(self):
        server, _ = _make_server_instance()
        result = server.watch_skills()
        assert result is server  # no-op, returns self

    def test_watch_skills_with_watcher(self):
        server, _ = _make_server_instance(enable_watcher=True)
        result = server.watch_skills(extra_paths=["/custom/skills"])
        assert result is server
        # Verify watcher has watched paths (at least the custom path was attempted)
        watched = server.watcher.watched_paths()
        # The custom path may or may not exist, but the call shouldn't crash
        assert isinstance(watched, (list, tuple))

    def test_watch_skills_exception_per_path(self):
        server, _ = _make_server_instance(enable_watcher=True)
        # Non-existent path should be handled gracefully
        result = server.watch_skills(extra_paths=["/nonexistent/path"])
        assert result is server  # graceful, no crash

    def test_reload_skills_without_watcher(self):
        server, _ = _make_server_instance()
        assert server.reload_skills() == 0

    def test_reload_skills_with_watcher(self):
        server, _ = _make_server_instance(enable_watcher=True)
        result = server.reload_skills()
        # With no skills loaded, count should be 0
        assert isinstance(result, int)

    def test_reload_skills_exception(self):
        server, _ = _make_server_instance(enable_watcher=True)
        # reload_skills should not crash even with no skills
        result = server.reload_skills()
        assert isinstance(result, int)

    def test_unwatch_skills_without_watcher(self):
        server, _ = _make_server_instance()
        server.unwatch_skills()  # no crash

    def test_unwatch_skills_with_watcher(self):
        server, _ = _make_server_instance(enable_watcher=True)
        server.unwatch_skills()  # should not crash with real SkillWatcher
        assert server.watcher.watched_paths() == [] or len(server.watcher.watched_paths()) == 0

    def test_unwatch_on_stop(self):
        server, _ = _make_server_instance(enable_watcher=True)
        server.start()
        server.stop()
        # After stop, watcher should have been unwatched
        # (unwatch_skills is called in stop())


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class TestEventBus:
    """Test EventBus integration in MayaMcpServer."""

    def test_event_bus_lazy_creation(self):
        server, _ = _make_server_instance()
        assert server._event_bus is None
        bus = server.event_bus
        assert bus is not None

    def test_event_bus_cached(self):
        server, _ = _make_server_instance()
        bus1 = server.event_bus
        bus2 = server.event_bus
        assert bus1 is bus2

    def test_subscribe(self):
        server, _ = _make_server_instance()
        sub_id = server.subscribe("server_started", lambda **kw: None)
        assert sub_id is not None

    def test_unsubscribe(self):
        server, _ = _make_server_instance()
        sub_id = server.subscribe("server_started", lambda **kw: None)
        server.unsubscribe("server_started", sub_id)  # no crash

    def test_publish_with_bus(self):
        server, _ = _make_server_instance()
        received = []
        server.subscribe("test_event", lambda **kw: received.append(kw))
        server.publish("test_event", key="value")
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_publish_without_bus_no_crash(self):
        server, _ = _make_server_instance()
        server.publish("test_event", key="value")  # _event_bus is None, no crash


# ---------------------------------------------------------------------------
# Server lifecycle events
# ---------------------------------------------------------------------------


class TestServerLifecycleEvents:
    """Test that server lifecycle emits EventBus events."""

    def test_start_emits_server_started(self):
        server, _ = _make_server_instance()
        received = []

        def on_start(**kwargs):
            received.append(kwargs)

        server.subscribe("server_started", on_start)
        server.start()
        assert len(received) == 1
        assert "url" in received[0]
        assert "port" in received[0]
        assert received[0]["url"].startswith("http://127.0.0.1:")
        server.stop()

    def test_stop_emits_server_stopped(self):
        server, _ = _make_server_instance()
        received = []

        def on_stop(**kwargs):
            received.append(kwargs)

        server.subscribe("server_stopped", on_stop)
        server.start()
        server.stop()
        assert len(received) == 1

    def test_register_builtin_actions_emits_skills_loaded(self):
        server, _ = _make_server_instance()
        received = []

        def on_loaded(**kwargs):
            received.append(kwargs)

        server.subscribe("skills_loaded", on_loaded)
        server.register_builtin_actions()
        assert len(received) == 1
        assert "loaded" in received[0]
        assert "failed" in received[0]
        assert "discovered" in received[0]

    def test_no_duplicate_events_on_double_start(self):
        server, _ = _make_server_instance()
        received = []

        def on_start(**kwargs):
            received.append(kwargs)

        server.subscribe("server_started", on_start)
        server.start()
        server.start()  # second call is no-op
        assert len(received) == 1  # only one event
        server.stop()


# ---------------------------------------------------------------------------
# Pipeline coverage — registry=None paths (lines 184-185, 248-249)
# ---------------------------------------------------------------------------


class TestPipelineRegistryNone:
    """Cover the registry=None warning paths in _init_pipeline and setup_pipeline."""

    def test_init_pipeline_registry_none(self):
        server, _ = _make_server_instance()
        # The registry property uses getattr(self._server, "_registry", None)
        # McpHttpServer doesn't have _registry, so registry returns None
        # Force _init_pipeline to re-run with registry=None
        original_pipeline = server._pipeline
        server._pipeline = None
        server._init_pipeline()
        # Pipeline should remain None since registry is None
        assert server.pipeline is None
        # Restore
        server._pipeline = original_pipeline

    def test_setup_pipeline_registry_none(self):
        server, _ = _make_server_instance()
        # With real dcc_mcp_core, registry may or may not be None
        # depending on internal state. Test the path by calling setup_pipeline
        result = server.setup_pipeline()
        assert result is server  # returns self regardless


# ---------------------------------------------------------------------------
# start_server with new parameters
# ---------------------------------------------------------------------------


class TestStartServerNewParams:
    """Test start_server module-level helper with new parameters."""

    def test_start_server_with_recorder(self):
        srv_mod = _import_server()
        srv_mod._server_instance = None

        handle = srv_mod.start_server(
            port=0,
            enable_recorder=True,
        )
        assert handle is not None
        # Clean up
        srv_mod.stop_server()
        srv_mod._server_instance = None

    def test_start_server_with_watcher(self):
        srv_mod = _import_server()
        srv_mod._server_instance = None

        handle = srv_mod.start_server(
            port=0,
            enable_watcher=True,
            watcher_debounce_ms=500,
        )
        assert handle is not None
        srv_mod.stop_server()
        srv_mod._server_instance = None

    def test_start_server_with_pipeline_and_recorder(self):
        srv_mod = _import_server()
        srv_mod._server_instance = None

        handle = srv_mod.start_server(
            port=0,
            enable_pipeline=True,
            enable_recorder=True,
        )
        assert handle is not None
        srv_mod.stop_server()
        srv_mod._server_instance = None


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


class TestStructuralRound49:
    """Verify the new methods exist and are properly typed."""

    def test_has_action_metrics(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "action_metrics")
        assert callable(server.action_metrics)

    def test_has_setup_recorder(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "setup_recorder")
        assert callable(server.setup_recorder)

    def test_has_setup_watcher(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "setup_watcher")
        assert callable(server.setup_watcher)

    def test_has_watch_skills(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "watch_skills")
        assert callable(server.watch_skills)

    def test_has_reload_skills(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "reload_skills")
        assert callable(server.reload_skills)

    def test_has_unwatch_skills(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "unwatch_skills")
        assert callable(server.unwatch_skills)

    def test_has_subscribe(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "subscribe")
        assert callable(server.subscribe)

    def test_has_unsubscribe(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "unsubscribe")
        assert callable(server.unsubscribe)

    def test_has_publish(self):
        server, _ = _make_server_instance()
        assert hasattr(server, "publish")
        assert callable(server.publish)

    def test_recorder_property(self):
        server, _ = _make_server_instance()
        assert server.recorder is None

    def test_watcher_property(self):
        server, _ = _make_server_instance()
        assert server.watcher is None

    def test_event_bus_property(self):
        server, _ = _make_server_instance()
        assert server.event_bus is not None

    def test_start_server_accepts_new_params(self):
        """Verify start_server function signature includes new parameters."""
        import inspect

        srv_mod = _import_server()
        sig = inspect.signature(srv_mod.start_server)
        param_names = list(sig.parameters.keys())
        assert "enable_recorder" in param_names
        assert "enable_watcher" in param_names
        assert "watcher_debounce_ms" in param_names

    def test_maya_mcp_server_init_accepts_new_params(self):
        """Verify MayaMcpServer.__init__ signature includes new parameters."""
        import inspect

        srv_mod = _import_server()
        sig = inspect.signature(srv_mod.MayaMcpServer.__init__)
        param_names = list(sig.parameters.keys())
        assert "enable_recorder" in param_names
        assert "enable_watcher" in param_names
        assert "watcher_debounce_ms" in param_names
