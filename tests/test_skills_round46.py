"""Round 46 tests: in-process skill executor correctness (issue #108, #122).

Verifies that the register_handler-based in-process executor:
1. Loads skill scripts via importlib without spawning subprocesses.
2. Calls main(**params) directly so kwargs reach the skill function.
3. Returns the dict returned by main(), not a fake placeholder.
4. Handles missing main(), loader errors, and skill_exception paths.
5. Installs the core global in-process executor instead of per-action handlers.
6. Delegates dynamic load_skill calls through the core skill client.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_server(with_dispatcher=False):
    """Construct a bare MayaMcpServer without starting it."""
    from dcc_mcp_maya.server import MayaMcpServer

    server = object.__new__(MayaMcpServer)
    server._dcc_name = "maya"
    server._config = MagicMock()
    server._handle = None
    server._maya_dispatcher = None
    # Readiness binder is created in ``__init__``; bypassing it means
    # we must supply a stand-in so ``attach_dispatcher`` can re-bind.
    server._readiness = MagicMock()

    # Mock the inner McpHttpServer with a registry and handler tracking
    mock_inner = MagicMock()
    mock_inner.has_handler.return_value = False
    mock_inner.registry = MagicMock()
    mock_inner.registry.list_actions_enabled.return_value = []
    mock_inner.registry.get_action.return_value = None
    server._server = mock_inner
    server._skill_client = MagicMock()

    if with_dispatcher:
        dispatcher = MagicMock()
        dispatcher.submit_callable.side_effect = lambda rid, fn, affinity="main": {
            "success": True,
            "output": fn(),
            "error": None,
        }
        server._maya_dispatcher = dispatcher

    return server


def _make_server_with_actions(actions):
    """Construct a server whose registry reports the given action dicts."""
    server = _make_server()
    server._server.registry.list_actions_enabled.return_value = actions
    server._server.registry.get_action.side_effect = lambda name: next(
        (a for a in actions if a.get("name") == name), None
    )
    return server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_skill(tmp_path):
    """Write a minimal skill script to a temp file and return its path."""

    def _write(body: str) -> Path:
        p = tmp_path / "test_skill.py"
        p.write_text(textwrap.dedent(body))
        return p

    return _write


# ---------------------------------------------------------------------------
# 1. core host execution bridge replaces per-action register_handler wiring
# ---------------------------------------------------------------------------


class TestExecutorRegistration:
    def test_removed_per_action_wiring_does_not_register_handlers(self):
        """Regression for #136: Maya no longer skips because a subprocess handler exists."""
        server = _make_server_with_actions([{"name": "test__skill", "source_file": "x.py", "enabled": True}])
        assert not hasattr(server, "_wire_in_process_executor")
        assert not hasattr(server, "_register_inprocess_handlers")
        server._server.register_handler.assert_not_called()

    def test_attach_dispatcher_installs_core_dispatcher_and_executor(self):
        from dcc_mcp_maya.server import MayaMcpServer

        server = object.__new__(MayaMcpServer)
        server._dcc_name = "maya"
        server._config = MagicMock(sandbox_policy=None)
        server._server = MagicMock()
        # Readiness binder created in ``__init__``; supply a stand-in
        # so ``attach_dispatcher`` can re-bind without crashing.
        server._readiness = MagicMock()
        dispatcher = MagicMock()
        server.attach_dispatcher(dispatcher)
        server._server.attach_dispatcher.assert_called_once_with(dispatcher)
        server._server.set_in_process_executor.assert_called_once()


# ---------------------------------------------------------------------------
# 2. run_skill_script — the core script-execution helper
# ---------------------------------------------------------------------------


class TestRunSkillScript:
    """Tests for the module-level run_skill_script helper."""

    def _run(self, script_path, params):
        from dcc_mcp_maya._executor import run_skill_script

        return run_skill_script(str(script_path), params)

    def test_params_forwarded_to_main(self, tmp_skill):
        """main() must receive the params dict as kwargs."""
        script = tmp_skill("""\
            def main(**kwargs):
                return {"success": True, "message": "ok", "got": kwargs}
        """)
        result = self._run(script, {"radius": 2.0, "name": "test"})
        assert result["success"] is True
        assert result["got"] == {"radius": 2.0, "name": "test"}

    def test_empty_params_ok(self, tmp_skill):
        script = tmp_skill("""\
            def main(**kwargs):
                return {"success": True, "message": "no params", "kwargs": kwargs}
        """)
        result = self._run(script, {})
        assert result["success"] is True
        assert result["kwargs"] == {}

    def test_result_dict_returned_as_is(self, tmp_skill):
        script = tmp_skill("""\
            def main(**kwargs):
                return {"success": True, "message": "sphere created", "context": {"name": "pSphere1"}}
        """)
        result = self._run(script, {})
        assert result["message"] == "sphere created"
        assert result["context"]["name"] == "pSphere1"

    def test_skill_entry_decorator_works(self, tmp_skill):
        """@skill_entry decorated main() must also work correctly."""
        script = tmp_skill("""\
            from dcc_mcp_core.skill import skill_entry, skill_success

            @skill_entry
            def main(radius: float = 1.0, **kwargs):
                return skill_success("Created", radius=radius)
        """)
        result = self._run(script, {"radius": 3.0})
        assert result["success"] is True
        assert result["context"]["radius"] == 3.0

    def test_if_name_main_guard_not_required(self, tmp_skill):
        """Script without the if __name__=='__main__' guard still works."""
        script = tmp_skill("""\
            _computed = 42

            def main(**kwargs):
                return {"success": True, "message": "works", "val": _computed}
        """)
        result = self._run(script, {})
        assert result["val"] == 42

    def test_missing_main_returns_error(self, tmp_skill):
        script = tmp_skill("x = 1  # no main() defined\n")
        result = self._run(script, {})
        assert result["success"] is False
        assert "main()" in result["message"]

    def test_nonexistent_script_returns_error(self):
        result = self._run("/nonexistent/path/skill.py", {})
        assert result["success"] is False

    def test_main_raises_exception_returns_error(self, tmp_skill):
        script = tmp_skill("""\
            def main(**kwargs):
                raise ValueError("boom")
        """)
        result = self._run(script, {})
        assert result["success"] is False
        assert "boom" in str(result.get("error", "") or result.get("message", ""))

    def test_loader_error_returns_error(self, tmp_skill):
        """SyntaxError in script body must return error, not raise."""
        script = tmp_skill("def main(**kwargs\n    pass\n")  # syntax error
        result = self._run(script, {})
        assert result["success"] is False

    def test_systemexit_in_main_is_handled(self, tmp_skill):
        """sys.exit() inside main() must not crash the executor."""
        script = tmp_skill("""\
            import sys
            def main(**kwargs):
                sys.exit(0)
        """)
        result = self._run(script, {})
        assert isinstance(result, dict)

    def test_mcp_result_attribute_honoured(self, tmp_skill):
        """If a script sets __mcp_result__ at module level, return it."""
        script = tmp_skill("""\
            __mcp_result__ = {"success": True, "message": "pre-computed"}
        """)
        result = self._run(script, {})
        assert result["message"] == "pre-computed"


# ---------------------------------------------------------------------------
# 3. _execute_in_process — dispatcher routing integration
# ---------------------------------------------------------------------------


class TestExecuteInProcess:
    def test_runs_directly_without_dispatcher(self, tmp_skill):
        """Without a dispatcher, scripts run on the calling thread directly."""
        script = tmp_skill("def main(**kwargs):\n    return {'success': True, 'message': 'direct'}\n")
        from dcc_mcp_maya import _executor

        server = _make_server()
        result = _executor.execute_in_process(server, str(script), {}, "test__action")
        assert result["success"] is True
        assert result["message"] == "direct"

    def test_routes_through_dispatcher_when_attached(self, tmp_skill, monkeypatch):
        """With a MayaUiDispatcher attached + off main thread, submit_callable must be called.

        The off-main-thread monkey-patch is required because pytest runs on
        Python's main thread, and dispatching to ``submit_callable`` from
        the main thread would deadlock waiting for itself. Production
        always reaches this code path from a hyper / tokio worker thread.
        """
        script = tmp_skill("def main(**kwargs):\n    return {'success': True, 'message': 'dispatched'}\n")
        from dcc_mcp_maya import _executor

        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        server = _make_server(with_dispatcher=True)
        result = _executor.execute_in_process(server, str(script), {}, "test__action")
        server._maya_dispatcher.submit_callable.assert_called_once()
        assert result["success"] is True

    def test_dispatcher_failure_returns_error(self, tmp_skill, monkeypatch):
        """If the dispatcher returns success=False, _execute_in_process wraps it."""
        script = tmp_skill("def main(**kwargs):\n    return {}\n")
        from dcc_mcp_maya import _executor

        monkeypatch.setattr(_executor, "_on_main_thread", lambda: False)

        server = _make_server()
        dispatcher = MagicMock()
        dispatcher.submit_callable.return_value = {
            "success": False,
            "output": None,
            "error": "Interrupted",
        }
        server._maya_dispatcher = dispatcher
        result = _executor.execute_in_process(server, str(script), {}, "test__action")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# 4. Dynamic load_skill auto-registers handlers (issue #122 regression guard)
# ---------------------------------------------------------------------------


class TestDynamicLoadSkill:
    def test_load_skill_uses_core_global_executor(self, tmp_skill):
        """load_skill() no longer registers per-action handlers that subprocess can win."""
        _ = tmp_skill("def main(**kwargs):\n    return {'success': True}\n")
        server = _make_server()
        server._skill_client.load_skill = MagicMock(return_value=True)

        result = server.load_skill("my-skill")
        assert result is True
        server._skill_client.load_skill.assert_called_once_with("my-skill")
        server._server.register_handler.assert_not_called()

    def test_load_skill_empty_result_no_handlers(self):
        """load_skill() with no actions returned must not call register_handler."""
        server = _make_server()
        server._skill_client.load_skill = MagicMock(return_value=True)
        result = server.load_skill("empty-skill")
        assert result is True
        server._skill_client.load_skill.assert_called_once_with("empty-skill")
        server._server.register_handler.assert_not_called()

    def test_load_skill_exception_returns_false(self):
        """load_skill() must return False and not raise when inner load fails."""
        server = _make_server()
        server._skill_client.load_skill = MagicMock(side_effect=ValueError("not found"))
        result = server.load_skill("missing-skill")
        assert result is False
