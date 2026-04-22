"""Unit tests for ``tools/check_doc_parity.py`` (issue #88)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_doc_parity.py"


@pytest.fixture(scope="module")
def parity():
    """Load the tool module once for the whole test file."""
    spec = importlib.util.spec_from_file_location("_check_doc_parity_uut", _TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_check_doc_parity_uut"] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_zh_mirror_is_always_reported(parity, tmp_path):
    """A docs/foo.md with no docs/zh/foo.md must fail regardless of allowlist."""
    _write(tmp_path / "guide" / "foo.md", "# Foo\n\n## Bar\n")
    # ZH root does not even exist.
    errors = parity.check_parity(tmp_path, allowlist={"guide/foo.md"})
    assert any("MISSING ZH" in e and "guide/foo.md" in e for e in errors)


def test_heading_parity_matches(parity, tmp_path):
    """Identical heading outlines produce zero errors."""
    en = "# Title\n\n## Section\n\n### Sub\n\n```py\nx = 1\n```\n"
    zh = "# 标题\n\n## 小节\n\n### 子\n\n```py\nx = 1\n```\n"
    _write(tmp_path / "guide" / "ok.md", en)
    _write(tmp_path / "zh" / "guide" / "ok.md", zh)
    assert parity.check_parity(tmp_path) == []


def test_heading_drift_detected(parity, tmp_path):
    """A ZH file missing a H3 must surface a HEADING MISMATCH."""
    en = "# Title\n\n## A\n\n### A.1\n\n## B\n"
    zh = "# 标题\n\n## A\n\n## B\n"  # lost ### A.1
    _write(tmp_path / "api" / "x.md", en)
    _write(tmp_path / "zh" / "api" / "x.md", zh)
    errors = parity.check_parity(tmp_path)
    assert any("HEADING MISMATCH" in e and "api/x.md" in e for e in errors)


def test_fence_count_mismatch_detected(parity, tmp_path):
    """Identical headings but a dropped code fence must still fail."""
    en = "# T\n\n## S\n\n```py\nx\n```\n\n```py\ny\n```\n"
    zh = "# T\n\n## S\n\n```py\nx\n```\n"  # lost the second fenced block
    _write(tmp_path / "guide" / "code.md", en)
    _write(tmp_path / "zh" / "guide" / "code.md", zh)
    errors = parity.check_parity(tmp_path)
    # Same heading outline, so only the fence mismatch should fire.
    assert any("FENCE MISMATCH" in e for e in errors)
    assert not any("HEADING MISMATCH" in e for e in errors)


def test_allowlist_suppresses_heading_drift(parity, tmp_path):
    """A path in the allowlist must silence HEADING / FENCE errors."""
    en = "# T\n\n## A\n\n### A.1\n"
    zh = "# 标\n\n## A\n"  # different outline
    _write(tmp_path / "guide" / "legacy.md", en)
    _write(tmp_path / "zh" / "guide" / "legacy.md", zh)
    # No allowlist → fails.
    assert parity.check_parity(tmp_path)
    # With allowlist → passes.
    assert parity.check_parity(tmp_path, allowlist={"guide/legacy.md"}) == []


def test_headings_inside_code_fences_are_ignored(parity, tmp_path):
    """A ``# ...`` line inside a fenced block must not count as a heading."""
    en = "# T\n\n## Shell\n\n```bash\n# not a heading\n```\n"
    zh = "# T\n\n## Shell\n\n```bash\n# 不是标题\n```\n"
    _write(tmp_path / "guide" / "shell.md", en)
    _write(tmp_path / "zh" / "guide" / "shell.md", zh)
    assert parity.check_parity(tmp_path) == []


def test_node_modules_and_index_are_skipped(parity, tmp_path):
    """Vendored trees and the landing page are exempt from the check."""
    # Landing page — EN only, no ZH mirror required.
    _write(tmp_path / "index.md", "# Landing\n")
    # Vendored README — EN only, no ZH mirror required.
    _write(tmp_path / "node_modules" / "some-pkg" / "README.md", "# Pkg\n")
    assert parity.check_parity(tmp_path) == []
