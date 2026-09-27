"""Guards for repository agent instruction files."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# `AGENTS.md` is the single agent contract file at the repository root. Every
# mainstream agent runtime reads it natively (Claude Code falls back to it when
# no CLAUDE.md exists), so vendor-specific files must not come back.
AGENT_ENTRYPOINTS = ("AGENTS.md",)
DEPRECATED_AGENT_ENTRYPOINTS = (
    "CLAUDE.md",
    "GEMINI.md",
    "COPILOT.md",
    "CODEBUDDY.md",
    "CURSOR.md",
    "OPENAI.md",
    "ANTHROPIC.md",
)
FORBIDDEN_MARKERS = (
    "BEGIN MULTICA-RUNTIME",
    "END MULTICA-RUNTIME",
    "Multica Agent Runtime",
)
FORBIDDEN_TRACKED_PREFIXES = (
    ".multica/",
    ".agent_context/",
)


def _tracked_files() -> list[str]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def test_agent_entrypoints_do_not_include_multica_runtime_context() -> None:
    tracked = set(_tracked_files())
    for relative_path in AGENT_ENTRYPOINTS:
        if relative_path not in tracked:
            continue
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            assert marker not in text, f"{relative_path} contains generated Multica marker {marker!r}"


def test_agents_md_is_the_only_agent_contract_file() -> None:
    tracked = set(_tracked_files())
    assert "AGENTS.md" in tracked, "AGENTS.md is the single agent contract file and must stay tracked"
    offenders = sorted(name for name in DEPRECATED_AGENT_ENTRYPOINTS if name in tracked)
    assert offenders == [], (
        "AGENTS.md is the single source of agent guidance; remove these vendor files and "
        f"fold their unique content into AGENTS.md: {offenders}"
    )


def test_multica_runtime_artifacts_are_not_tracked() -> None:
    tracked = _tracked_files()
    offenders = [
        path
        for path in tracked
        if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES)
    ]
    assert offenders == []
