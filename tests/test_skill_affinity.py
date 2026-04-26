"""Tests for ``tools/lint_skill_affinity.py`` and the bundled skill affinity.

Covers issue #84 acceptance criteria:

- Every bundled ``tools.yaml`` declares ``affinity`` and ``execution``.
- Every ``execution: async`` entry has a positive ``timeout_hint_secs``.
- The lint script exits 0 on the repository and non-zero on bad input.
- ``tools/annotate_skill_affinity.py`` is idempotent (running it again
  produces no changes on a freshly annotated tree).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "src" / "dcc_mcp_maya" / "skills"
LINT_SCRIPT = REPO_ROOT / "tools" / "lint_skill_affinity.py"
ANNOTATE_SCRIPT = REPO_ROOT / "tools" / "annotate_skill_affinity.py"


def _tools_yaml_paths() -> list[Path]:
    return sorted(SKILLS_ROOT.glob("*/tools.yaml"))


def test_every_tool_declares_affinity_and_execution():
    """Every bundled tool must declare execution + affinity (issue #84)."""
    missing: list[str] = []
    for path in _tools_yaml_paths():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for tool in data.get("tools", []) or []:
            name = tool.get("name", "<unnamed>")
            if "affinity" not in tool:
                missing.append(f"{path.parent.name}:{name} (no affinity)")
            if "execution" not in tool:
                missing.append(f"{path.parent.name}:{name} (no execution)")
    assert not missing, "Tools missing affinity/execution:\n  " + "\n  ".join(missing)


def test_async_tools_have_timeout_hint():
    """Every async tool must declare a positive ``timeout_hint_secs``."""
    bad: list[str] = []
    for path in _tools_yaml_paths():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for tool in data.get("tools", []) or []:
            if tool.get("execution") == "async":
                hint = tool.get("timeout_hint_secs")
                if not isinstance(hint, int) or hint <= 0:
                    bad.append(f"{path.parent.name}:{tool.get('name')} timeout_hint_secs={hint!r}")
    assert not bad, "Async tools with bad timeout_hint_secs:\n  " + "\n  ".join(bad)


def test_long_running_families_are_async():
    """Long-running skill families must have at least one async tool (#84)."""
    long_running_skills = {
        "maya-render",
        "maya-render-farm",
        "maya-texture-bake",
        "maya-shot-export",
    }
    for skill in long_running_skills:
        path = SKILLS_ROOT / skill / "tools.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        executions = {tool.get("execution") for tool in data.get("tools", []) or []}
        assert "async" in executions, f"{skill} declares no async tool but belongs to long-running family"


def test_lint_script_passes_on_repo():
    """The CI lint script must succeed on the current tree."""
    result = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--skills-root", str(SKILLS_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Affinity lint failed:\n{result.stdout}\n{result.stderr}"


def test_lint_script_rejects_missing_affinity(tmp_path: Path):
    """The lint script must exit non-zero when ``affinity`` is absent."""
    bad_skill = tmp_path / "bad-skill"
    bad_skill.mkdir()
    (bad_skill / "tools.yaml").write_text(
        "tools:\n- name: do_something\n  execution: sync\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--skills-root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "MISSING_AFFINITY" in result.stdout


def test_lint_script_rejects_async_without_timeout(tmp_path: Path):
    """Async tools missing ``timeout_hint_secs`` must fail the linter."""
    bad_skill = tmp_path / "bad-skill"
    bad_skill.mkdir()
    (bad_skill / "tools.yaml").write_text(
        "tools:\n- name: render_frames\n  execution: async\n  affinity: main\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(LINT_SCRIPT), "--skills-root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "MISSING_TIMEOUT_HINT" in result.stdout


@pytest.mark.skipif(not ANNOTATE_SCRIPT.exists(), reason="annotator script not present")
def test_annotator_is_idempotent():
    """Running the annotator on already-annotated files must be a no-op."""
    result = subprocess.run(
        [sys.executable, str(ANNOTATE_SCRIPT), "--skills-root", str(SKILLS_ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # "Annotated 0 of N" means no changes; the script always prints a summary line.
    assert "Annotated 0 of " in result.stdout, result.stdout
