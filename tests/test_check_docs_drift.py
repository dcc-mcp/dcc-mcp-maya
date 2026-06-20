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
