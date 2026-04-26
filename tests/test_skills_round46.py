"""Round 46 tests: in-process skill executor correctness (issue #108).

Verifies that _wire_in_process_executor produces an executor that:
1. Loads skill scripts via importlib without spawning subprocesses.
2. Calls main(**params) directly so kwargs reach the skill function.
3. Returns the dict returned by main(), not a fake placeholder.
4. Handles missing main(), loader errors, and skill_exception paths.
5. Is registered on the SkillCatalog via set_in_process_executor.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_server():
    """Construct a bare MayaMcpServer without starting it."""
    from dcc_mcp_maya.server import MayaMcpServer

    server = object.__new__(MayaMcpServer)
    server._dcc_name = "maya"
    server._config = MagicMock()
    server._handle = None
    server._server = MagicMock()
    return server


def _extract_executor(server):
    """Call _wire_in_process_executor and capture the registered callable."""
    captured = {}

    def fake_set_in_process_executor(fn):
        captured["fn"] = fn

    server._server.catalog.set_in_process_executor = fake_set_in_process_executor
    server._wire_in_process_executor()
    return captured.get("fn")


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
# 1. Executor is registered on catalog
# ---------------------------------------------------------------------------


class TestExecutorRegistration:
    def test_registers_on_catalog(self):
        server = _make_server()
        executor = _extract_executor(server)
        assert callable(executor), "executor must be callable"

    def test_skips_when_catalog_missing(self):
        server = _make_server()
        del server._server.catalog
        server._wire_in_process_executor()  # must not raise

    def test_skips_when_method_missing(self):
        server = _make_server()
        del server._server.catalog.set_in_process_executor
        server._wire_in_process_executor()  # must not raise


# ---------------------------------------------------------------------------
# 2. Executor calls main(**params) — the critical correctness test
# ---------------------------------------------------------------------------


class TestExecutorCallsMain:
    def test_params_forwarded_to_main(self, tmp_skill):
        """main() must receive the params dict as kwargs."""
        script = tmp_skill("""\
            def main(**kwargs):
                return {"success": True, "message": "ok", "got": kwargs}
        """)
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {"radius": 2.0, "name": "test"})
        assert result["success"] is True
        assert result["got"] == {"radius": 2.0, "name": "test"}

    def test_empty_params_ok(self, tmp_skill):
        script = tmp_skill("""\
            def main(**kwargs):
                return {"success": True, "message": "no params", "kwargs": kwargs}
        """)
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
        assert result["success"] is True
        assert result["kwargs"] == {}

    def test_result_dict_returned_as_is(self, tmp_skill):
        script = tmp_skill("""\
            def main(**kwargs):
                return {"success": True, "message": "sphere created", "context": {"name": "pSphere1"}}
        """)
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
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
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {"radius": 3.0})
        assert result["success"] is True
        assert result["context"]["radius"] == 3.0

    def test_if_name_main_guard_not_required(self, tmp_skill):
        """Script without the if __name__=='__main__' guard still works."""
        script = tmp_skill("""\
            _computed = 42

            def main(**kwargs):
                return {"success": True, "message": "works", "val": _computed}
        """)
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
        assert result["val"] == 42


# ---------------------------------------------------------------------------
# 3. Error handling
# ---------------------------------------------------------------------------


class TestExecutorErrorHandling:
    def test_missing_main_returns_error(self, tmp_skill):
        script = tmp_skill("x = 1  # no main() defined\n")
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
        assert result["success"] is False
        assert "main()" in result["message"]

    def test_nonexistent_script_returns_error(self):
        server = _make_server()
        executor = _extract_executor(server)
        result = executor("/nonexistent/path/skill.py", {})
        assert result["success"] is False

    def test_main_raises_exception_returns_error(self, tmp_skill):
        script = tmp_skill("""\
            def main(**kwargs):
                raise ValueError("boom")
        """)
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
        assert result["success"] is False
        assert "boom" in str(result.get("error", "") or result.get("message", ""))

    def test_loader_error_returns_error(self, tmp_skill):
        """SyntaxError in script body must return error, not raise."""
        script = tmp_skill("def main(**kwargs\n    pass\n")  # syntax error
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
        assert result["success"] is False

    def test_systemexit_in_main_is_handled(self, tmp_skill):
        """sys.exit() inside main() must not crash the executor."""
        script = tmp_skill("""\
            import sys
            def main(**kwargs):
                sys.exit(0)
        """)
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
        # Returns a safe fallback, does NOT raise SystemExit
        assert isinstance(result, dict)

    def test_mcp_result_attribute_honoured(self, tmp_skill):
        """If a script sets __mcp_result__ at module level, return it."""
        script = tmp_skill("""\
            __mcp_result__ = {"success": True, "message": "pre-computed"}
        """)
        server = _make_server()
        executor = _extract_executor(server)
        result = executor(str(script), {})
        assert result["message"] == "pre-computed"
