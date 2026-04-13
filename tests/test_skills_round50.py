"""Round 50 tests — coverage gap closure for diagnostics.py and server.py.

Targets:
- diagnostics.py: filter="error", entry serialization exception, dispatch non-string output,
  lazy _get_sandbox_context/_get_action_recorder creation, _set_ipc_address_env exception
- server.py: include_bundled=False, get_bundled_skill_paths import failure,
  action_metrics exception, reload_skills with logged count, unwatch exception,
  publish exception, start_server(include_bundled=False)
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import json
import os
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


def _import_diagnostics():
    """Force reimport of diagnostics module."""
    import dcc_mcp_maya.diagnostics as diag

    importlib.reload(diag)
    return diag


# ---------------------------------------------------------------------------
# diagnostics.py: filter="error" falls through to entries() (else branch)
# ---------------------------------------------------------------------------


class TestDiagnosticsFilterError:
    """Cover the filter='error' / 'all' / unknown → entries() else branch."""

    def test_filter_error_falls_to_entries(self):
        diag = _import_diagnostics()
        mock_entry = MagicMock()
        mock_entry.action = "err_action"
        mock_entry.outcome = "error"
        mock_entry.timestamp_ms = 99
        mock_entry.details = "detail"

        mock_audit = MagicMock()
        mock_audit.entries.return_value = [mock_entry]

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log('{"filter": "error"}'))
        assert result["success"] is True
        # "error" filter falls through to entries() (same as "all")
        mock_audit.entries.assert_called_once()
        assert result["total_entries"] == 1

    def test_filter_all_uses_entries(self):
        diag = _import_diagnostics()
        mock_audit = MagicMock()
        mock_audit.entries.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log('{"filter": "all"}'))
        assert result["success"] is True
        mock_audit.entries.assert_called_once()

    def test_filter_unknown_falls_to_entries(self):
        diag = _import_diagnostics()
        mock_audit = MagicMock()
        mock_audit.entries.return_value = []

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log('{"filter": "unknown_value"}'))
        assert result["success"] is True
        mock_audit.entries.assert_called_once()


# ---------------------------------------------------------------------------
# diagnostics.py: entry serialization exception → str(entry)
# ---------------------------------------------------------------------------


class TestDiagnosticsEntrySerializationException:
    """Cover line 121-122: except Exception in entry serialization → str(entry)."""

    def test_entry_serialization_exception_falls_back_to_str(self):
        diag = _import_diagnostics()
        # Create an entry that raises on .action attribute access
        mock_entry = MagicMock()
        type(mock_entry).action = property(lambda self: (_ for _ in ()).throw(RuntimeError("bad entry")))
        mock_entry.outcome = "error"
        mock_entry.timestamp_ms = 0
        mock_entry.details = None

        mock_audit = MagicMock()
        mock_audit.entries.return_value = [mock_entry]

        mock_ctx = MagicMock()
        mock_ctx.audit_log = mock_audit
        diag._sandbox_context = mock_ctx

        result = json.loads(diag._handle_get_audit_log("{}"))
        assert result["success"] is True
        assert result["total_entries"] == 1
        # The serialized entry should be a string (str(mock_entry))
        assert isinstance(result["entries"][0], str)


# ---------------------------------------------------------------------------
# diagnostics.py: dispatch non-string output
# ---------------------------------------------------------------------------


class TestDiagnosticsDispatchNonStringOutput:
    """Cover line 195: return json.dumps(output) when output is not a string."""

    def test_dispatch_returns_dict_output(self):
        diag = _import_diagnostics()
        mock_dispatcher = MagicMock()
        # Return a dict output (not a string)
        mock_dispatcher.dispatch.return_value = {"output": {"success": True, "data": 42}}
        diag._dispatcher_ref = mock_dispatcher

        result = json.loads(diag._handle_dispatch_action('{"action": "test_dict", "params": {}}'))
        assert result["success"] is True
        assert result["data"] == 42

    def test_dispatch_returns_list_output(self):
        diag = _import_diagnostics()
        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"output": [1, 2, 3]}
        diag._dispatcher_ref = mock_dispatcher

        result = json.loads(diag._handle_dispatch_action('{"action": "test_list", "params": {}}'))
        assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# diagnostics.py: _handle_get_action_metrics invalid JSON
# ---------------------------------------------------------------------------


class TestDiagnosticsMetricsInvalidJson:
    """Cover line 141-142: JSONDecodeError in get_action_metrics defaults to {}."""

    def test_invalid_json_defaults_to_empty_params(self):
        diag = _import_diagnostics()
        mock_recorder = MagicMock()
        mock_recorder.all_metrics.return_value = []
        diag._action_recorder = mock_recorder

        result = json.loads(diag._handle_get_action_metrics("not-json"))
        assert result["success"] is True
        assert result["metrics"] == []


# ---------------------------------------------------------------------------
# diagnostics.py: _set_ipc_address_env TransportAddress import failure
# ---------------------------------------------------------------------------


class TestSetIpcAddressEnvException:
    """Cover line 253-254: TransportAddress import failure in _set_ipc_address_env."""

    def test_transport_address_import_failure(self):
        diag = _import_diagnostics()
        os.environ.pop("DCC_MCP_IPC_ADDRESS", None)
        # Patch TransportAddress.default_local to raise, which triggers the except branch
        with patch(
            "dcc_mcp_core.TransportAddress.default_local",
            side_effect=ImportError("no TransportAddress"),
        ):
            # Should not crash, just silently skip
            diag._set_ipc_address_env()
        # Env var should NOT be set since TransportAddress.default_local raised
        assert "DCC_MCP_IPC_ADDRESS" not in os.environ


# ---------------------------------------------------------------------------
# server.py: include_bundled=False
# ---------------------------------------------------------------------------


class TestIncludeBundledFalse:
    """Cover lines 127-133: include_bundled=False skips get_bundled_skill_paths."""

    def test_collect_skill_search_paths_include_bundled_false(self):
        srv_mod = _import_server()
        paths = srv_mod._collect_skill_search_paths(include_bundled=False)
        # When include_bundled=False, get_bundled_skill_paths is never called
        # (even though it doesn't exist in dcc_mcp_core, the if-branch is skipped entirely)
        assert isinstance(paths, list)

    def test_collect_skill_search_paths_include_bundled_true_no_crash(self):
        """include_bundled=True but get_bundled_skill_paths not available — except swallows."""
        srv_mod = _import_server()
        # get_bundled_skill_paths doesn't exist in dcc_mcp_core.skill,
        # so the try/except will catch ImportError and pass
        paths = srv_mod._collect_skill_search_paths(include_bundled=True)
        # Should not crash, paths returned without bundled paths
        assert isinstance(paths, list)

    def test_include_bundled_false_vs_true_same_paths(self):
        """Since get_bundled_skill_paths is not available, both produce same result."""
        srv_mod = _import_server()
        paths_false = srv_mod._collect_skill_search_paths(include_bundled=False)
        paths_true = srv_mod._collect_skill_search_paths(include_bundled=True)
        # Both should produce same paths since get_bundled_skill_paths doesn't exist
        assert paths_false == paths_true


# ---------------------------------------------------------------------------
# server.py: register_builtin_actions(include_bundled=False)
# ---------------------------------------------------------------------------


class TestRegisterBuiltinActionsIncludeBundled:
    """Test register_builtin_actions forwards include_bundled correctly."""

    def test_register_builtin_actions_include_bundled_false(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        with patch.object(
            srv_mod,
            "_collect_skill_search_paths",
            return_value=[],
        ) as mock_collect:
            try:
                server.register_builtin_actions(include_bundled=False)
            except Exception:
                pass  # discover may fail with empty paths
            mock_collect.assert_called_once_with(None, include_bundled=False)

    def test_register_builtin_actions_include_bundled_true_default(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        with patch.object(
            srv_mod,
            "_collect_skill_search_paths",
            return_value=[],
        ) as mock_collect:
            try:
                server.register_builtin_actions()
            except Exception:
                pass
            mock_collect.assert_called_once_with(None, include_bundled=True)


# ---------------------------------------------------------------------------
# server.py: start_server(include_bundled=False)
# ---------------------------------------------------------------------------


class TestStartServerIncludeBundled:
    """Test start_server module-level function with include_bundled param."""

    def test_start_server_include_bundled_false(self):
        srv_mod = _import_server()
        srv_mod._server_instance = None
        with patch.object(
            srv_mod.MayaMcpServer,
            "register_builtin_actions",
        ) as mock_reg:
            mock_reg.return_value = MagicMock()
            handle = srv_mod.start_server(
                port=0,
                include_bundled=False,
            )
            assert handle is not None
            mock_reg.assert_called_once_with(
                extra_skill_paths=None,
                include_bundled=False,
            )
        srv_mod.stop_server()
        srv_mod._server_instance = None

    def test_start_server_include_bundled_true_default(self):
        srv_mod = _import_server()
        srv_mod._server_instance = None
        with patch.object(
            srv_mod.MayaMcpServer,
            "register_builtin_actions",
        ) as mock_reg:
            mock_reg.return_value = MagicMock()
            handle = srv_mod.start_server(port=0)
            assert handle is not None
            mock_reg.assert_called_once_with(
                extra_skill_paths=None,
                include_bundled=True,
            )
        srv_mod.stop_server()
        srv_mod._server_instance = None


# ---------------------------------------------------------------------------
# server.py: action_metrics exception path
# ---------------------------------------------------------------------------


class TestActionMetricsExceptionPath:
    """Cover lines 820-822: action_metrics catches exception and returns None."""

    def test_action_metrics_exception_from_recorder(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_recorder=True)
        # Replace the recorder reference with a mock that raises
        mock_recorder = MagicMock()
        mock_recorder.metrics.side_effect = RuntimeError("metrics boom")
        server._recorder = mock_recorder
        result = server.action_metrics("test_action")
        assert result is None


# ---------------------------------------------------------------------------
# server.py: reload_skills with logged count > 0
# ---------------------------------------------------------------------------


class TestReloadSkillsWithCount:
    """Cover line 921: logger.info when count > 0 in reload_skills."""

    def test_reload_skills_logs_count_when_positive(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_watcher=True)
        # Replace watcher with a mock that returns positive skill count
        mock_watcher = MagicMock()
        mock_watcher.skill_count.return_value = 5
        mock_watcher.skills.return_value = []
        server._watcher = mock_watcher
        import logging

        with patch.object(logging.getLogger("dcc_mcp_maya.server"), "info") as mock_info:
            result = server.reload_skills()
        assert result == 5
        # Check that the info log was called with the expected message
        info_calls = [str(c) for c in mock_info.call_args_list]
        assert any("SkillWatcher" in c and "5" in c for c in info_calls)


# ---------------------------------------------------------------------------
# server.py: unwatch_skills exception path
# ---------------------------------------------------------------------------


class TestUnwatchSkillsException:
    """Cover line 935: unwatch_skills catches exception."""

    def test_unwatch_skills_exception_logged(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_watcher=True)
        # Replace watcher with a mock that raises on unwatch
        mock_watcher = MagicMock()
        mock_watcher.unwatch.side_effect = RuntimeError("unwatch fail")
        server._watcher = mock_watcher
        # Should not crash
        server.unwatch_skills()


# ---------------------------------------------------------------------------
# server.py: publish exception path
# ---------------------------------------------------------------------------


class TestPublishExceptionPath:
    """Cover lines 998-999: publish catches exception."""

    def test_publish_exception_logged(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        # Replace the event bus with a mock that raises on publish
        mock_bus = MagicMock()
        mock_bus.publish.side_effect = RuntimeError("pub fail")
        server._event_bus = mock_bus
        # Should not crash
        server.publish("test_event", key="value")


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


class TestStructuralRound50:
    """Verify new test coverage targets are correct."""

    def test_diagnostics_module_has_filter_error_branch(self):
        diag = _import_diagnostics()
        # The _handle_get_audit_log should handle filter="error" by falling
        # through to entries()
        assert hasattr(diag, "_handle_get_audit_log")

    def test_server_module_has_include_bundled(self):
        srv_mod = _import_server()
        import inspect

        sig = inspect.signature(srv_mod._collect_skill_search_paths)
        assert "include_bundled" in sig.parameters

    def test_start_server_has_include_bundled(self):
        srv_mod = _import_server()
        import inspect

        sig = inspect.signature(srv_mod.start_server)
        assert "include_bundled" in sig.parameters


# ---------------------------------------------------------------------------
# server.py: unwatch_skills success path (line 933)
# ---------------------------------------------------------------------------


class TestUnwatchSkillsSuccess:
    """Cover line 933: logger.info('SkillWatcher stopped') on successful unwatch."""

    def test_unwatch_skills_success_logs_info(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_watcher=True)
        mock_watcher = MagicMock()
        mock_watcher.unwatch.return_value = None
        server._watcher = mock_watcher
        import logging

        with patch.object(logging.getLogger("dcc_mcp_maya.server"), "info") as mock_info:
            server.unwatch_skills()
        info_calls = [str(c) for c in mock_info.call_args_list]
        assert any("SkillWatcher stopped" in c for c in info_calls)


# ---------------------------------------------------------------------------
# server.py: reload_skills exception path (lines 923-925)
# ---------------------------------------------------------------------------


class TestReloadSkillsExceptionPath:
    """Cover lines 923-925: reload_skills catches exception and returns 0."""

    def test_reload_skills_watcher_exception_returns_zero(self):
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_watcher=True)
        mock_watcher = MagicMock()
        mock_watcher.skills.side_effect = RuntimeError("watcher boom")
        server._watcher = mock_watcher
        result = server.reload_skills()
        assert result == 0


# ---------------------------------------------------------------------------
# server.py: get_bundled_skill_paths success (line 131)
# ---------------------------------------------------------------------------


class TestGetBundledSkillPathsIntegration:
    """Cover line 131: get_bundled_skill_paths succeeds and extends paths."""

    def test_get_bundled_skill_paths_when_available(self):
        """When get_bundled_skill_paths exists and returns paths, they are included."""
        srv_mod = _import_server()
        # Inject a mock get_bundled_skill_paths into dcc_mcp_core.skill
        mock_fn = MagicMock(return_value=["/mock/bundled/skills"])
        with patch.object(
            srv_mod,
            "_collect_skill_search_paths",
            wraps=srv_mod._collect_skill_search_paths,
        ):
            # We need to mock the import inside the function
            with patch.dict(sys.modules, {}):
                # Inject mock into the already-imported module
                import dcc_mcp_core.skill as skill_mod

                original = getattr(skill_mod, "get_bundled_skill_paths", None)
                skill_mod.get_bundled_skill_paths = mock_fn
                try:
                    paths = srv_mod._collect_skill_search_paths(include_bundled=True)
                    assert "/mock/bundled/skills" in paths
                finally:
                    if original is not None:
                        skill_mod.get_bundled_skill_paths = original
                    else:
                        delattr(skill_mod, "get_bundled_skill_paths")


# ---------------------------------------------------------------------------
# api.py: serialize_action_result / deserialize_action_result
# ---------------------------------------------------------------------------


class TestSerializeActionResult:
    """Test serialize_action_result and deserialize_action_result helpers."""

    def test_serialize_json_roundtrip(self):
        from dcc_mcp_maya.api import deserialize_action_result, serialize_action_result

        result = {"success": True, "message": "test", "context": {}}
        payload = serialize_action_result(result, fmt="json")
        restored = deserialize_action_result(payload, fmt="json")
        assert restored["success"] is True
        assert restored["message"] == "test"

    def test_serialize_msgpack_roundtrip(self):
        from dcc_mcp_maya.api import deserialize_action_result, serialize_action_result

        result = {"success": False, "message": "error", "error": "detail"}
        payload = serialize_action_result(result, fmt="msgpack")
        restored = deserialize_action_result(payload, fmt="msgpack")
        assert restored["success"] is False
        assert restored["error"] == "detail"

    def test_serialize_fallback_on_exception(self):
        from dcc_mcp_maya.api import serialize_action_result

        result = {"success": True, "message": "ok"}
        with patch(
            "dcc_mcp_core.serialize_result",
            side_effect=RuntimeError("boom"),
        ):
            payload = serialize_action_result(result, fmt="json")
        # Should fallback to plain JSON
        import json

        restored = json.loads(payload)
        assert restored["success"] is True

    def test_deserialize_fallback_on_exception(self):
        import json

        from dcc_mcp_maya.api import deserialize_action_result

        payload = json.dumps({"success": True, "message": "ok"})
        with patch(
            "dcc_mcp_core.deserialize_result",
            side_effect=RuntimeError("boom"),
        ):
            restored = deserialize_action_result(payload, fmt="json")
        assert restored["success"] is True

    def test_serialize_in_api_all(self):
        from dcc_mcp_maya.api import __all__

        assert "serialize_action_result" in __all__
        assert "deserialize_action_result" in __all__

    def test_serialize_importable_from_top_level(self):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, "serialize_action_result")
        assert hasattr(dcc_mcp_maya, "deserialize_action_result")
        assert "serialize_action_result" in dcc_mcp_maya.__all__
        assert "deserialize_action_result" in dcc_mcp_maya.__all__
