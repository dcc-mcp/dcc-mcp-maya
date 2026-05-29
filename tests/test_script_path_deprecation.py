"""Issue #311 — ``script_path`` is a deprecated alias for ``file_path``.

``execute_python`` / ``execute_mel`` keep accepting ``script_path`` for one
release so external MCP clients do not break, but they now emit a
``DeprecationWarning`` pointing callers at ``file_path``. This is the
predecessor cleanup that unblocks dropping the alias from the dcc-mcp-core
``DccApiExecutor`` wire schema (dcc-mcp-core#1391 / #1392).

The tests below exercise the shared ``_resolve_script_file_path`` resolver in
both skill scripts without requiring a live Maya — the warning fires purely
from parameter resolution.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from tests.conftest import load_skill_script

_MIGRATION = "script_path` is deprecated, use `file_path`"


def _resolver(script_name: str):
    mod = load_skill_script("maya-scripting", script_name)
    return mod._resolve_script_file_path


@pytest.mark.parametrize("script_name", ["execute_python", "execute_mel"])
class TestScriptPathDeprecation:
    def test_script_path_emits_deprecation_warning(self, script_name: str):
        resolve = _resolver(script_name)
        with pytest.warns(DeprecationWarning, match="script_path"):
            resolved = resolve({"script_path": "/abs/path/to/thing"})
        assert resolved == "/abs/path/to/thing"

    def test_warning_message_includes_migration_string(self, script_name: str):
        resolve = _resolver(script_name)
        with pytest.warns(DeprecationWarning) as record:
            resolve({"script_path": "/abs/path/to/thing"})
        assert any(_MIGRATION in str(w.message) for w in record)

    def test_file_path_is_silent(self, script_name: str):
        resolve = _resolver(script_name)
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            resolved = resolve({"file_path": "/abs/path/to/thing"})
        assert resolved == "/abs/path/to/thing"

    def test_file_path_wins_and_is_silent_when_both_present(self, script_name: str):
        resolve = _resolver(script_name)
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            resolved = resolve({"file_path": "/keep/me", "script_path": "/old/alias"})
        assert resolved == "/keep/me"

    def test_inline_code_path_is_silent(self, script_name: str):
        """Inline ``code`` callers never touch the file resolver / warning."""
        resolve = _resolver(script_name)
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            assert resolve({"code": "1 + 1"}) is None

    def test_empty_script_path_is_silent(self, script_name: str):
        resolve = _resolver(script_name)
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            assert resolve({"script_path": "   "}) is None


def test_execute_python_file_path_runs_without_warning(tmp_path: Path):
    mod = load_skill_script("maya-scripting", "execute_python")
    f = tmp_path / "demo.py"
    f.write_text("print('from-file-path')\n", encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        out = mod.execute_python(file_path=str(f))
    assert out.get("success") is True
    assert "from-file-path" in (out.get("context") or {}).get("stdout", "")


def test_execute_python_script_path_still_runs_with_warning(tmp_path: Path):
    mod = load_skill_script("maya-scripting", "execute_python")
    f = tmp_path / "demo.py"
    f.write_text("print('from-script-path-alias')\n", encoding="utf-8")
    with pytest.warns(DeprecationWarning, match="script_path"):
        out = mod.execute_python(script_path=str(f))
    assert out.get("success") is True
    assert "from-script-path-alias" in (out.get("context") or {}).get("stdout", "")
