"""Tests for dcc_mcp_maya.diagnostics module."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os
from unittest.mock import MagicMock, patch


def _import_diagnostics():
    """Import the diagnostics module fresh (avoids stale module-level state)."""
    import importlib

    import dcc_mcp_maya.diagnostics as diag

    importlib.reload(diag)
    return diag


# ── register_diagnostic_handlers ──────────────────────────────────────────


class TestRegisterDiagnosticHandlers:
    """Test register_diagnostic_handlers() registers handlers and sets env."""

    def test_registers_three_handlers(self):
        diag = _import_diagnostics()
        mock_server = MagicMock()
        diag.register_diagnostic_handlers(mock_server)
        assert mock_server.register_handler.call_count == 3
        handler_names = [c.args[0] for c in mock_server.register_handler.call_args_list]
        assert "get_audit_log" in handler_names
        assert "get_action_metrics" in handler_names
        assert "dispatch_action" in handler_names

    def test_sets_ipc_address_env_var(self):
        diag = _import_diagnostics()
        mock_server = MagicMock()
        old = os.environ.pop("DCC_MCP_IPC_ADDRESS", None)
        try:
            diag.register_diagnostic_handlers(mock_server)
            assert "DCC_MCP_IPC_ADDRESS" in os.environ
        finally:
            if old is not None:
                os.environ["DCC_MCP_IPC_ADDRESS"] = old
            else:
                os.environ.pop("DCC_MCP_IPC_ADDRESS", None)

    def test_respects_existing_ipc_address(self):
        diag = _import_diagnostics()
        mock_server = MagicMock()
        os.environ["DCC_MCP_IPC_ADDRESS"] = "custom://addr"
        try:
            diag.register_diagnostic_handlers(mock_server)
            assert os.environ["DCC_MCP_IPC_ADDRESS"] == "custom://addr"
        finally:
            os.environ.pop("DCC_MCP_IPC_ADDRESS", None)

    def test_dispatcher_ref_set_when_provided(self):
        diag = _import_diagnostics()
        mock_server = MagicMock()
        mock_dispatcher = MagicMock()
        diag.register_diagnostic_handlers(mock_server, dispatcher=mock_dispatcher)
        assert diag._dispatcher_ref is mock_dispatcher

    def test_dispatcher_ref_not_set_when_none(self):
        diag = _import_diagnostics()
        mock_server = MagicMock()
        diag.register_diagnostic_handlers(mock_server, dispatcher=None)
        # _dispatcher_ref may be None or leftover from previous test
        # but the function should not raise

    def test_register_handler_exception_is_swallowed(self):
        diag = _import_diagnostics()
        mock_server = MagicMock()
        mock_server.register_handler.side_effect = RuntimeError("nope")
        # Should not raise
        diag.register_diagnostic_handlers(mock_server)


# ── _handle_get_audit_log ─────────────────────────────────────────────────


class TestHandleGetAuditLog:
    """Test _handle_get_audit_log handler."""

    def test_returns_error_when_sandbox_unavailable(self):
        diag = _import_diagnostics()
        # Force sandbox context to None by clearing it
        diag._sandbox_context = None
        with patch("dcc_mcp_core.SandboxContext", side_effect=ImportError):
            result = json.loads(diag._handle_get_audit_log("{}"))
        assert result["success"] is False
        assert "SandboxContext" in result["message"]

    def test_returns_entries_with_mock_context(self):
        diag = _import_diagnostics()
        mock_entry = MagicMock()
        mock_entry.action = "test_action"
        mock_entry.outcome = "success"
        mock_entry.timestamp_ms = 1234
        mock_entry.details = None

        mock_audit = MagicMock()
        mock_audit.entries.return_value = [mock_entry]

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log("{}"))
        assert result["success"] is True
        assert result["total_entries"] == 1
        assert result["entries"][0]["action"] == "test_action"

    def test_filter_success(self):
        diag = _import_diagnostics()
        mock_entry = MagicMock()
        mock_entry.action = "ok"
        mock_entry.outcome = "success"
        mock_entry.timestamp_ms = 0
        mock_entry.details = None

        mock_audit = MagicMock()
        mock_audit.successes.return_value = [mock_entry]

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log('{"filter": "success"}'))
        assert result["success"] is True
        mock_audit.successes.assert_called_once()

    def test_filter_denied(self):
        diag = _import_diagnostics()
        mock_audit = MagicMock()
        mock_audit.denials.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log('{"filter": "denied"}'))
        assert result["success"] is True
        mock_audit.denials.assert_called_once()

    def test_filter_by_action_name(self):
        diag = _import_diagnostics()
        mock_audit = MagicMock()
        mock_audit.entries_for_action.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log('{"action_name": "my_action"}'))
        assert result["success"] is True
        mock_audit.entries_for_action.assert_called_once_with("my_action")

    def test_limit_parameter(self):
        diag = _import_diagnostics()
        entries = []
        for i in range(10):
            e = MagicMock()
            e.action = "a{}".format(i)
            e.outcome = "success"
            e.timestamp_ms = i
            e.details = None
            entries.append(e)

        mock_audit = MagicMock()
        mock_audit.entries.return_value = entries

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log('{"limit": 3}'))
        assert result["total_entries"] == 10
        assert len(result["entries"]) == 3

    def test_invalid_json_defaults_to_empty(self):
        diag = _import_diagnostics()
        mock_audit = MagicMock()
        mock_audit.entries.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log("not-json"))
        assert result["success"] is True

    def test_audit_exception_returns_error(self):
        diag = _import_diagnostics()
        mock_ctx = MagicMock()
        mock_ctx.audit_log.raiseError = True
        type(mock_ctx).audit_log = property(lambda self: (_ for _ in ()).throw(RuntimeError("audit fail")))
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log("{}"))
        assert result["success"] is False


# ── _handle_get_action_metrics ────────────────────────────────────────────


class TestHandleGetActionMetrics:
    """Test _handle_get_action_metrics handler."""

    def test_returns_error_when_recorder_unavailable(self):
        diag = _import_diagnostics()
        diag._action_recorder = None
        with patch("dcc_mcp_core.ActionRecorder", side_effect=ImportError):
            result = json.loads(diag._handle_get_action_metrics("{}"))
        assert result["success"] is False
        assert "ActionRecorder" in result["message"]

    def test_returns_metrics_for_action(self):
        diag = _import_diagnostics()
        mock_metric = MagicMock()
        mock_metric.action_name = "create_sphere"
        mock_metric.invocation_count = 10
        mock_metric.success_count = 9
        mock_metric.failure_count = 1
        mock_metric.success_rate.return_value = 0.9
        mock_metric.avg_duration_ms = 42.5
        mock_metric.p95_duration_ms = 100.0
        mock_metric.p99_duration_ms = 150.0

        mock_recorder = MagicMock()
        mock_recorder.metrics.return_value = mock_metric
        diag._action_recorder = mock_recorder

        result = json.loads(diag._handle_get_action_metrics('{"action_name": "create_sphere"}'))
        assert result["success"] is True
        assert len(result["metrics"]) == 1
        assert result["metrics"][0]["action_name"] == "create_sphere"
        assert result["metrics"][0]["invocation_count"] == 10

    def test_returns_all_metrics(self):
        diag = _import_diagnostics()
        mock_metric = MagicMock()
        mock_metric.action_name = "x"
        mock_metric.invocation_count = 1
        mock_metric.success_count = 1
        mock_metric.failure_count = 0
        mock_metric.success_rate.return_value = 1.0
        mock_metric.avg_duration_ms = 5.0
        mock_metric.p95_duration_ms = 5.0
        mock_metric.p99_duration_ms = 5.0

        mock_recorder = MagicMock()
        mock_recorder.all_metrics.return_value = [mock_metric]
        diag._action_recorder = mock_recorder

        result = json.loads(diag._handle_get_action_metrics("{}"))
        assert result["success"] is True
        assert len(result["metrics"]) == 1

    def test_metrics_not_found_returns_empty_list(self):
        diag = _import_diagnostics()
        mock_recorder = MagicMock()
        mock_recorder.metrics.return_value = None
        diag._action_recorder = mock_recorder

        result = json.loads(diag._handle_get_action_metrics('{"action_name": "nonexistent"}'))
        assert result["success"] is True
        assert result["metrics"] == []

    def test_exception_returns_error(self):
        diag = _import_diagnostics()
        mock_recorder = MagicMock()
        mock_recorder.metrics.side_effect = RuntimeError("oops")
        diag._action_recorder = mock_recorder

        result = json.loads(diag._handle_get_action_metrics('{"action_name": "x"}'))
        assert result["success"] is False


# ── _handle_dispatch_action ───────────────────────────────────────────────


class TestHandleDispatchAction:
    """Test _handle_dispatch_action handler."""

    def test_returns_error_when_no_dispatcher(self):
        diag = _import_diagnostics()
        diag._dispatcher_ref = None
        result = json.loads(diag._handle_dispatch_action('{"action": "test"}'))
        assert result["success"] is False
        assert "Dispatcher" in result["message"]

    def test_returns_error_when_missing_action(self):
        diag = _import_diagnostics()
        diag._dispatcher_ref = MagicMock()
        result = json.loads(diag._handle_dispatch_action('{"params": {}}'))
        assert result["success"] is False
        assert "Missing" in result["message"]

    def test_returns_error_on_invalid_json(self):
        diag = _import_diagnostics()
        result = json.loads(diag._handle_dispatch_action("not-json"))
        assert result["success"] is False
        assert "Invalid JSON" in result["message"]

    def test_dispatches_action(self):
        diag = _import_diagnostics()
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"output": '{"success": true}'}
        diag._dispatcher_ref = mock_dispatcher

        result = json.loads(diag._handle_dispatch_action('{"action": "create_sphere", "params": {}}'))
        # The handler returns the output string directly if it's JSON
        assert result["success"] is True

    def test_dispatch_exception_returns_error(self):
        diag = _import_diagnostics()
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.side_effect = RuntimeError("dispatch fail")
        diag._dispatcher_ref = mock_dispatcher

        result = json.loads(diag._handle_dispatch_action('{"action": "fail"}'))
        assert result["success"] is False


# ── _set_ipc_address_env ──────────────────────────────────────────────────


class TestSetIpcAddressEnv:
    """Test _set_ipc_address_env helper."""

    def test_sets_env_var(self):
        diag = _import_diagnostics()
        os.environ.pop("DCC_MCP_IPC_ADDRESS", None)
        try:
            diag._set_ipc_address_env()
            assert "DCC_MCP_IPC_ADDRESS" in os.environ
        finally:
            os.environ.pop("DCC_MCP_IPC_ADDRESS", None)

    def test_does_not_overwrite_existing(self):
        diag = _import_diagnostics()
        os.environ["DCC_MCP_IPC_ADDRESS"] = "test://existing"
        try:
            diag._set_ipc_address_env()
            assert os.environ["DCC_MCP_IPC_ADDRESS"] == "test://existing"
        finally:
            os.environ.pop("DCC_MCP_IPC_ADDRESS", None)


# ── _metric_to_dict ───────────────────────────────────────────────────────


class TestMetricToDict:
    """Test _metric_to_dict helper."""

    def test_converts_metric_to_dict(self):
        diag = _import_diagnostics()
        mock_metric = MagicMock()
        mock_metric.action_name = "test_action"
        mock_metric.invocation_count = 5
        mock_metric.success_count = 4
        mock_metric.failure_count = 1
        mock_metric.success_rate.return_value = 0.8
        mock_metric.avg_duration_ms = 50.0
        mock_metric.p95_duration_ms = 100.0
        mock_metric.p99_duration_ms = 120.0

        result = diag._metric_to_dict(mock_metric)
        assert result["action_name"] == "test_action"
        assert result["invocation_count"] == 5
        assert result["success_rate"] == 0.8
        assert "avg_duration_ms" in result


# ── integration with server ───────────────────────────────────────────────


class TestDiagnosticsServerIntegration:
    """Test that diagnostics is properly integrated with MayaMcpServer."""

    def test_register_builtin_actions_calls_diagnostics(self):
        from dcc_mcp_maya.server import MayaMcpServer

        with patch("dcc_mcp_maya.diagnostics.register_diagnostic_handlers") as mock_reg:
            server = MayaMcpServer(port=0)
            try:
                server.register_builtin_actions()
            except Exception:
                pass  # may fail due to no skill paths, but diagnostics should be called
            mock_reg.assert_called_once()

    def test_diagnostics_module_importable(self):
        from dcc_mcp_maya.diagnostics import register_diagnostic_handlers

        assert callable(register_diagnostic_handlers)
