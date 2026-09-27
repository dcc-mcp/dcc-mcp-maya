"""Guards for repository agent instruction files.

`AGENTS.md` is the **single hand-written agent contract file** at the repo root
(plan C, PIP-3736). Vendor-named entry points (`CLAUDE.md`, `GEMINI.md`,
`CURSOR.md`, `OPENAI.md`, `ANTHROPIC.md`, `COPILOT.md`, `CODEBUDDY.md`) and root
rule files (`.cursorrules`, `.clinerules`, `.windsurfrules`) are deliberately
absent so guidance cannot drift across N hand-maintained copies. Vendor-specific
integration notes live under `docs/integrations/` and are linked from `AGENTS.md`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The only agent contract file allowed at the repo root.
AGENT_ENTRYPOINTS = ("AGENTS.md",)

# Root files that must NOT exist: each one re-introduces N-way drift.
FORBIDDEN_ROOT_AGENT_FILES = (
    "CLAUDE.md",
    "GEMINI.md",
    "COPILOT.md",
    "CODEBUDDY.md",
    "CURSOR.md",
    "ANTHROPIC.md",
    "OPENAI.md",
    ".cursorrules",
    ".clinerules",
    ".windsurfrules",
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


def test_agent_contract_is_single_sourced_at_root() -> None:
    """`AGENTS.md` is the only agent contract file; vendor duplicates stay out."""
    present = [name for name in FORBIDDEN_ROOT_AGENT_FILES if (REPO_ROOT / name).exists()]
    assert present == [], (
        "`AGENTS.md` is the single source of agent guidance. Vendor-specific notes belong "
        f"under `docs/integrations/`; remove these root files: {present}"
    )


def test_multica_runtime_artifacts_are_not_tracked() -> None:
    tracked = _tracked_files()
    offenders = [
        path
        for path in tracked
        if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES)
    ]
    assert offenders == []
