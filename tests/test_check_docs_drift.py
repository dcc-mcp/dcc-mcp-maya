"""Unit tests for ``tools/check_docs_drift.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_docs_drift.py"


@pytest.fixture(scope="module")
def drift():
    spec = importlib.util.spec_from_file_location("_check_docs_drift_uut", _TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_check_docs_drift_uut"] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_tools_list(path: Path, names: list[str]) -> Path:
    payload = {"tools": [{"name": name} for name in names]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_count_claim_exact_and_plus(drift, tmp_path):
    _write(tmp_path / "README.md", "We ship **3 tools** and **2+ typed Maya tools**.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["a", "b", "c"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    assert issues and issues[0].severity == "warning"


def test_stale_inline_tool_reference_is_reported(drift, tmp_path):
    _write(tmp_path / "docs" / "guide.md", "Use `load_skill` and `missing_tool`.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["load_skill"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    assert any(issue.code == "STALE_TOOL_REF" for issue in issues)


def test_undocumented_tools_only_warn(drift, tmp_path):
    _write(tmp_path / "docs" / "guide.md", "Use `load_skill`.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["load_skill", "search_tools"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    assert any(issue.code == "UNDOCUMENTED_TOOLS" for issue in issues)
    assert not any(issue.severity == "error" for issue in issues)


def test_markdown_fences_are_ignored(drift, tmp_path):
    _write(
        tmp_path / "docs" / "guide.md",
        "Count is **2 tools**.\n\n```text\n`missing_tool`\n```\n",
    )
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["present_tool"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    assert any(issue.code == "TOOL_COUNT_MISMATCH" for issue in issues)
    assert not any(issue.code == "STALE_TOOL_REF" for issue in issues)


def test_hyphenated_names_are_not_tool_refs(drift, tmp_path):
    """Hyphenated names like `maya-scene` are skill names, not MCP tools."""
    _write(tmp_path / "README.md", "Load `maya-scene` and `maya-primitives`.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["load_skill"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    assert not any(issue.code == "STALE_TOOL_REF" for issue in issues)


def test_single_underscore_tool_names_are_matched(drift, tmp_path):
    """Single-underscore tool names like `load_skill` are valid MCP tools."""
    _write(tmp_path / "README.md", "Call `load_skill`.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["other_tool"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    assert any(issue.code == "STALE_TOOL_REF" for issue in issues)


def test_double_underscore_tool_names_are_matched(drift, tmp_path):
    """Double-underscore tool names like `dcc_introspect__list_module` are valid."""
    _write(tmp_path / "README.md", "Call `dcc_introspect__list_module`.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["other_tool"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    # Double-underscore is valid snake_case, should be matched
    assert any(issue.code == "STALE_TOOL_REF" for issue in issues)


def test_snake_case_names_are_tool_refs(drift, tmp_path):
    """Single-underscore names like `maya_success` match the tool-like pattern.
    
    We cannot distinguish between Python API functions (maya_success) and
    MCP tool names (load_skill) by regex alone — both are valid snake_case.
    The check is intentionally inclusive; false positives in STALE_TOOL_REF
    are acceptable as warnings that don't block CI.
    """
    _write(tmp_path / "README.md", "Use `maya_success` and `with_maya`.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["load_skill"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    # These are valid snake_case tokens — they WILL trigger STALE_TOOL_REF
    assert any(issue.code == "STALE_TOOL_REF" for issue in issues)


def test_package_names_with_hyphens_are_not_tool_refs(drift, tmp_path):
    """Package names like `dcc-mcp-maya` with hyphens are not tools."""
    _write(tmp_path / "README.md", "Import `dcc-mcp-maya`.\n")
    tools_list = _write_tools_list(tmp_path / "tools-list.json", ["load_skill"])
    issues = drift.check_docs_drift(tmp_path, tools_list)
    assert not any(issue.code == "STALE_TOOL_REF" for issue in issues)


@pytest.mark.parametrize("content, expected", [("", "empty"), ("{", "invalid")])
def test_main_reports_bad_tools_list(drift, tmp_path, capsys, content, expected):
    _write(tmp_path / "README.md", "We ship **1 tool**.\n")
    tools_list = _write(tmp_path / "tools-list.json", content)

    exit_code = drift.main(["--repo-root", str(tmp_path), "--tools-list", str(tools_list)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert expected in captured.err.lower()
