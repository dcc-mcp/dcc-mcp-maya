"""Round 47 — ActionPipeline integration tests for MayaMcpServer.

Tests the new pipeline middleware feature:
- enable_pipeline flag in __init__
- setup_pipeline() fluent API
- audit_records() / last_elapsed_ms() queries
- start_server(enable_pipeline=True)
- Structural checks (pipeline property, middleware names)
"""
# Import future modules
from __future__ import annotations

# Import built-in modules
import inspect
import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helper: create a MayaMcpServer with mock dcc_mcp_core
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_dcc_mcp_core():
    """Mock dcc_mcp_core for testing without the real library."""
    mock_core = MagicMock()

    # ActionRegistry mock
    mock_registry = MagicMock()
    mock_registry.search_actions.return_value = []
    mock_registry.get_categories.return_value = ["geometry"]
    mock_registry.get_tags.return_value = ["mesh"]
    mock_registry.unregister.return_value = True
    mock_core.ActionRegistry.return_value = mock_registry

    # ActionDispatcher mock
    mock_dispatcher = MagicMock()
    mock_core.ActionDispatcher.return_value = mock_dispatcher

    # ActionPipeline mock with realistic middleware API
    mock_pipeline = MagicMock()
    mock_pipeline.middleware_count.return_value = 4
    mock_pipeline.middleware_names.return_value = ["logging", "timing", "audit", "rate_limit"]
    mock_pipeline.handler_count.return_value = 0
    mock_pipeline.register_handler.return_value = None

    # Audit middleware mock
    mock_audit = MagicMock()
    mock_audit.record_count.return_value = 0
    mock_audit.records.return_value = []
    mock_audit.records_for_action.return_value = []
    mock_pipeline.add_audit.return_value = mock_audit

    # Timing middleware mock
    mock_timing = MagicMock()
    mock_timing.last_elapsed_ms.return_value = 42.5
    mock_pipeline.add_timing.return_value = mock_timing

    mock_pipeline.add_logging.return_value = None
    mock_pipeline.add_rate_limit.return_value = None
    mock_core.ActionPipeline.return_value = mock_pipeline

    # McpHttpConfig mock
    mock_config = MagicMock()
    mock_config.port = 0
    mock_core.McpHttpConfig.return_value = mock_config

    # create_skill_manager mock
    mock_server = MagicMock()
    mock_server.discover.return_value = 0
    mock_server.list_skills.return_value = []
    mock_server.start.return_value = MagicMock(
        mcp_url=MagicMock(return_value="http://127.0.0.1:0/mcp"),
        port=0,
        shutdown=MagicMock(),
    )
    mock_server._registry = mock_registry
    mock_server.find_skills.return_value = []
    mock_server.is_loaded.return_value = False
    mock_server.get_skill_info.return_value = None
    mock_server.has_handler.return_value = False
    mock_server.register_handler.return_value = None
    mock_core.create_skill_manager.return_value = mock_server

    # Env helpers
    mock_core.get_app_skill_paths_from_env.return_value = []
    mock_core.get_skill_paths_from_env.return_value = []
    mock_core.get_skills_dir.return_value = ""

    # DccCapabilities
    mock_caps = MagicMock()
    mock_caps.scene_manager = True
    mock_core.DccCapabilities.return_value = mock_caps

    # Step 1: Install the mock core FIRST so any re-import of dcc_mcp_maya
    #         will find our mock instead of the real dcc_mcp_core.
    saved = {}
    saved["dcc_mcp_core"] = sys.modules.get("dcc_mcp_core")
    sys.modules["dcc_mcp_core"] = mock_core

    # Step 2: Now evict all cached dcc_mcp_maya modules.  Because the mock
    #         core is already in sys.modules, the next `import dcc_mcp_maya.server`
    #         will use our mock.
    _maya_mods = sorted(
        (k for k in list(sys.modules) if k == "dcc_mcp_maya" or k.startswith("dcc_mcp_maya.")),
        reverse=True,  # delete sub-modules before parent packages
    )
    for mod_name in _maya_mods:
        saved[mod_name] = sys.modules.pop(mod_name)

    yield {
        "core": mock_core,
        "registry": mock_registry,
        "dispatcher": mock_dispatcher,
        "pipeline": mock_pipeline,
        "audit": mock_audit,
        "timing": mock_timing,
        "server": mock_server,
        "config": mock_config,
    }

    # Restore: remove mock core and restore original modules
    for mod_name, orig in saved.items():
        if orig is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = orig


# ---------------------------------------------------------------------------
# Test: enable_pipeline=False (default) — no pipeline created
# ---------------------------------------------------------------------------


class TestPipelineDisabledByDefault:
    """When enable_pipeline=False (default), no pipeline is created."""

    def test_no_pipeline_by_default(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        assert srv.pipeline is None

    def test_no_audit_by_default(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        assert srv.audit_middleware is None

    def test_no_timing_by_default(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        assert srv.timing_middleware is None

    def test_audit_records_empty_when_disabled(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        assert srv.audit_records() == []

    def test_last_elapsed_none_when_disabled(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        assert srv.last_elapsed_ms("some_action") is None


# ---------------------------------------------------------------------------
# Test: enable_pipeline=True — pipeline created in __init__
# ---------------------------------------------------------------------------


class TestPipelineEnabledOnInit:
    """When enable_pipeline=True, pipeline is created with default middleware."""

    def test_pipeline_created(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        assert srv.pipeline is not None

    def test_audit_middleware_created(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        assert srv.audit_middleware is not None

    def test_timing_middleware_created(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        assert srv.timing_middleware is not None

    def test_pipeline_has_logging(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        MayaMcpServer(port=0, enable_pipeline=True)
        _mock_dcc_mcp_core["pipeline"].add_logging.assert_called_once_with(log_params=True)

    def test_pipeline_has_timing(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        MayaMcpServer(port=0, enable_pipeline=True)
        _mock_dcc_mcp_core["pipeline"].add_timing.assert_called_once()

    def test_pipeline_has_audit(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        MayaMcpServer(port=0, enable_pipeline=True)
        _mock_dcc_mcp_core["pipeline"].add_audit.assert_called_once_with(record_params=True)

    def test_pipeline_no_rate_limit_by_default(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        MayaMcpServer(port=0, enable_pipeline=True)
        _mock_dcc_mcp_core["pipeline"].add_rate_limit.assert_not_called()


# ---------------------------------------------------------------------------
# Test: setup_pipeline() fluent API
# ---------------------------------------------------------------------------


class TestSetupPipelineFluent:
    """setup_pipeline() allows fine-grained middleware configuration."""

    def test_returns_self(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        result = srv.setup_pipeline()
        assert result is srv

    def test_rate_limit_enabled(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        srv.setup_pipeline(rate_limit=True, rate_limit_max_calls=50, rate_limit_window_ms=500)
        _mock_dcc_mcp_core["pipeline"].add_rate_limit.assert_called_once_with(
            max_calls=50, window_ms=500,
        )

    def test_disable_timing(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        srv.setup_pipeline(timing=False)
        _mock_dcc_mcp_core["pipeline"].add_timing.assert_not_called()

    def test_disable_audit(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        srv.setup_pipeline(audit=False)
        _mock_dcc_mcp_core["pipeline"].add_audit.assert_not_called()

    def test_disable_logging(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        srv.setup_pipeline(log_params=False)
        _mock_dcc_mcp_core["pipeline"].add_logging.assert_not_called()


# ---------------------------------------------------------------------------
# Test: audit_records() and last_elapsed_ms() queries
# ---------------------------------------------------------------------------


class TestPipelineQueries:
    """Query audit trail and timing from the pipeline middleware."""

    def test_audit_records_all(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        records = srv.audit_records()
        assert isinstance(records, list)

    def test_audit_records_filtered(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        srv.audit_records(action_name="maya_scene__new_scene")
        _mock_dcc_mcp_core["audit"].records_for_action.assert_called_once_with(
            "maya_scene__new_scene",
        )

    def test_last_elapsed_ms(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        elapsed = srv.last_elapsed_ms("maya_scene__new_scene")
        assert elapsed == 42.5
        _mock_dcc_mcp_core["timing"].last_elapsed_ms.assert_called_once_with(
            "maya_scene__new_scene",
        )

    def test_last_elapsed_ms_exception(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        _mock_dcc_mcp_core["timing"].last_elapsed_ms.side_effect = RuntimeError("fail")
        assert srv.last_elapsed_ms("bad_action") is None

    def test_audit_records_exception(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0, enable_pipeline=True)
        _mock_dcc_mcp_core["audit"].records.side_effect = RuntimeError("fail")
        assert srv.audit_records() == []


# ---------------------------------------------------------------------------
# Test: start_server(enable_pipeline=True)
# ---------------------------------------------------------------------------


class TestStartServerWithPipeline:
    """start_server() supports enable_pipeline parameter."""

    def test_start_server_with_pipeline(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya import server

        # Reset singleton
        server._server_instance = None

        handle = server.start_server(port=0, enable_pipeline=True, register_builtins=False)
        assert handle is not None
        assert server._server_instance.pipeline is not None

        # Cleanup
        server.stop_server()

    def test_start_server_without_pipeline(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya import server

        # Reset singleton
        server._server_instance = None

        handle = server.start_server(port=0, enable_pipeline=False, register_builtins=False)
        assert handle is not None
        assert server._server_instance.pipeline is None

        # Cleanup
        server.stop_server()


# ---------------------------------------------------------------------------
# Test: setup_pipeline after start is a no-op
# ---------------------------------------------------------------------------


class TestSetupPipelineAfterStart:
    """setup_pipeline() after start() is a no-op (logs warning)."""

    def test_setup_pipeline_after_start_noop(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        srv.register_builtin_actions()
        _ = srv.start()
        # Calling setup_pipeline after start should return self without creating pipeline
        result = srv.setup_pipeline()
        assert result is srv
        # Pipeline should still be None because we didn't enable it before start
        assert srv.pipeline is None
        srv.stop()


# ---------------------------------------------------------------------------
# Test: Structural checks
# ---------------------------------------------------------------------------


class TestPipelineStructural:
    """Verify that new pipeline methods exist and are properly typed."""

    def test_has_setup_pipeline_method(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "setup_pipeline")
        assert callable(getattr(MayaMcpServer, "setup_pipeline"))

    def test_has_pipeline_property(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        assert srv.pipeline is None or srv.pipeline is not None

    def test_has_audit_middleware_property(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        _ = srv.audit_middleware

    def test_has_timing_middleware_property(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        srv = MayaMcpServer(port=0)
        _ = srv.timing_middleware

    def test_has_audit_records_method(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "audit_records")

    def test_has_last_elapsed_ms_method(self, _mock_dcc_mcp_core):
        from dcc_mcp_maya.server import MayaMcpServer

        assert hasattr(MayaMcpServer, "last_elapsed_ms")

    def test_enable_pipeline_param_in_init(self, _mock_dcc_mcp_core):
        """Verify __init__ accepts enable_pipeline parameter."""
        from dcc_mcp_maya.server import MayaMcpServer

        sig = inspect.signature(MayaMcpServer.__init__)
        assert "enable_pipeline" in sig.parameters
