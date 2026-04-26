"""Round 46 tests: in-process skill executor correctness (issue #108, #122).

Verifies that the register_handler-based in-process executor:
1. Loads skill scripts via importlib without spawning subprocesses.
2. Calls main(**params) directly so kwargs reach the skill function.
3. Returns the dict returned by main(), not a fake placeholder.
4. Handles missing main(), loader errors, and skill_exception paths.
5. Registers handlers via McpHttpServer.register_handler (core 0.14.x API).
6. Handles dynamic load_skill calls by registering handlers automatically.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, call

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

    # Mock the inner McpHttpServer with a registry and handler tracking
    mock_inner = MagicMock()
    mock_inner.has_handler.return_value = False
    mock_inner.registry = MagicMock()
    mock_inner.registry.list_actions_enabled.return_value = []
    mock_inner.registry.get_action.return_value = None
    server._server = mock_inner

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
# 1. _wire_in_process_executor uses register_handler (new core 0.14.x API)
# ---------------------------------------------------------------------------


class TestExecutorRegistration:
    def test_no_op_when_no_actions(self):
        """_wire_in_process_executor must not raise when no actions are loaded."""
        server = _make_server()
        server._wire_in_process_executor()  # must not raise

    def test_skips_when_registry_missing(self):
        """Gracefully skips when server.registry raises AttributeError."""
        server = _make_server()
        del server._server.registry
        server._wire_in_process_executor()  # must not raise

    def test_registers_handler_for_action_with_source_file(self, tmp_skill):
        """A handler is registered for every action that has a source_file."""
        script = tmp_skill("def main(**kwargs):\n    return {'success': True, 'message': 'ok'}\n")
        actions = [{"name": "test__skill", "source_file": str(script), "enabled": True}]
        server = _make_server_with_actions(actions)
        server._wire_in_process_executor()
        server._server.register_handler.assert_called_once()
        name_arg = server._server.register_handler.call_args[0][0]
        assert name_arg == "test__skill"

    def test_skips_action_without_source_file(self):
        """Actions with no source_file must be silently skipped."""
        actions = [{"name": "test__skill", "source_file": None, "enabled": True}]
        server = _make_server_with_actions(actions)
        server._wire_in_process_executor()
        server._server.register_handler.assert_not_called()

    def test_skips_action_with_existing_handler(self, tmp_skill):
        """Actions that already have a handler must not be double-registered."""
        script = tmp_skill("def main(**kwargs):\n    return {'success': True}\n")
        actions = [{"name": "test__skill", "source_file": str(script), "enabled": True}]
        server = _make_server_with_actions(actions)
        server._server.has_handler.return_value = True
        server._wire_in_process_executor()
        server._server.register_handler.assert_not_called()

    def test_registers_multiple_actions(self, tmp_path):
        """All actions with source_file get individual handlers."""
        scripts = []
        for i in range(3):
            p = tmp_path / f"skill_{i}.py"
            p.write_text("def main(**kwargs):\n    return {'success': True}\n")
            scripts.append(p)

        actions = [{"name": f"skill__{i}", "source_file": str(scripts[i]), "enabled": True} for i in range(3)]
        server = _make_server_with_actions(actions)
        server._wire_in_process_executor()
        assert server._server.register_handler.call_count == 3


# ---------------------------------------------------------------------------
# 2. _run_skill_script — the core script-execution helper
# ---------------------------------------------------------------------------


class TestRunSkillScript:
    """Tests for the module-level _run_skill_script helper (replaces the old
    inline _maya_in_process_executor closure)."""

    def _run(self, script_path, params):
        from dcc_mcp_maya.server import _run_skill_script

        return _run_skill_script(str(script_path), params)

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
        server = _make_server()
        result = server._execute_in_process(str(script), {}, "test__action")
        assert result["success"] is True
        assert result["message"] == "direct"

    def test_routes_through_dispatcher_when_attached(self, tmp_skill):
        """With a MayaUiDispatcher attached, submit_callable must be called."""
        script = tmp_skill("def main(**kwargs):\n    return {'success': True, 'message': 'dispatched'}\n")
        server = _make_server(with_dispatcher=True)
        result = server._execute_in_process(str(script), {}, "test__action")
        # Dispatcher was consulted
        server._maya_dispatcher.submit_callable.assert_called_once()
        assert result["success"] is True

    def test_dispatcher_failure_returns_error(self, tmp_skill):
        """If the dispatcher returns success=False, _execute_in_process wraps it."""
        script = tmp_skill("def main(**kwargs):\n    return {}\n")
        server = _make_server()
        dispatcher = MagicMock()
        dispatcher.submit_callable.return_value = {
            "success": False,
            "output": None,
            "error": "Interrupted",
        }
        server._maya_dispatcher = dispatcher
        result = server._execute_in_process(str(script), {}, "test__action")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# 4. Dynamic load_skill auto-registers handlers (issue #122 regression guard)
# ---------------------------------------------------------------------------


class TestDynamicLoadSkill:
    def test_load_skill_registers_handlers(self, tmp_skill):
        """load_skill() must register in-process handlers after inner load returns actions."""
        script = tmp_skill("def main(**kwargs):\n    return {'success': True}\n")
        server = _make_server()

        # Simulate inner server.load_skill() returning action names
        action_names = ["my_skill__action"]
        server._server.load_skill = MagicMock(return_value=action_names)
        server._server.registry.get_action.return_value = {
            "name": "my_skill__action",
            "source_file": str(script),
            "enabled": True,
        }

        result = server.load_skill("my-skill")
        assert result is True  # DccServerBase returns bool
        server._server.register_handler.assert_called_once()

    def test_load_skill_empty_result_no_handlers(self):
        """load_skill() with no actions returned must not call register_handler."""
        server = _make_server()
        server._server.load_skill = MagicMock(return_value=[])
        result = server.load_skill("empty-skill")
        assert result is True
        server._server.register_handler.assert_not_called()

    def test_load_skill_exception_returns_false(self):
        """load_skill() must return False and not raise when inner load fails."""
        server = _make_server()
        server._server.load_skill = MagicMock(side_effect=ValueError("not found"))
        result = server.load_skill("missing-skill")
        assert result is False
