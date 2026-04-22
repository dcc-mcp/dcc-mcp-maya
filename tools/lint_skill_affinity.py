#!/usr/bin/env python3
"""CI lint for ``execution``/``affinity`` in bundled ``tools.yaml`` files.

Fails (exit 1) when any bundled tool is missing ``affinity`` or when an
``execution: async`` tool is missing ``timeout_hint_secs``.  See issue #84
for the acceptance criteria.

Designed as a companion to :mod:`tools.annotate_skill_affinity` — the
annotator writes the fields, this linter enforces them in CI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


VALID_EXECUTION = {"sync", "async"}
VALID_AFFINITY = {"main", "any", "named"}


def lint_file(path: Path) -> List[Tuple[str, str]]:
    """Return a list of ``(rule, message)`` for every problem in *path*."""
    problems: List[Tuple[str, str]] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [("YAML_PARSE_ERROR", f"{path}: {exc}")]

    tools = data.get("tools")
    if not isinstance(tools, list):
        # Skills without tools.yaml payloads are skipped silently.
        return problems

    for tool in tools:
        if not isinstance(tool, dict):
            problems.append(("MALFORMED_TOOL", f"{path}: non-mapping entry {tool!r}"))
            continue

        name = tool.get("name", "<unnamed>")

        affinity = tool.get("affinity")
        if affinity is None:
            problems.append(("MISSING_AFFINITY", f"{path}: tool '{name}' has no affinity"))
        elif affinity not in VALID_AFFINITY:
            problems.append(
                ("INVALID_AFFINITY", f"{path}: tool '{name}' affinity={affinity!r} not in {sorted(VALID_AFFINITY)}")
            )

        execution = tool.get("execution")
        if execution is None:
            problems.append(("MISSING_EXECUTION", f"{path}: tool '{name}' has no execution"))
        elif execution not in VALID_EXECUTION:
            problems.append(
                ("INVALID_EXECUTION", f"{path}: tool '{name}' execution={execution!r} not in {sorted(VALID_EXECUTION)}")
            )

        if execution == "async":
            timeout = tool.get("timeout_hint_secs")
            if timeout is None:
                problems.append(
                    (
                        "MISSING_TIMEOUT_HINT",
                        f"{path}: async tool '{name}' has no timeout_hint_secs",
                    )
                )
            elif not isinstance(timeout, int) or timeout <= 0:
                problems.append(
                    (
                        "INVALID_TIMEOUT_HINT",
                        f"{path}: async tool '{name}' timeout_hint_secs must be a positive int, got {timeout!r}",
                    )
                )

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-root",
        default="src/dcc_mcp_maya/skills",
        help="Path to skills directory (default: src/dcc_mcp_maya/skills)",
    )
    args = parser.parse_args()

    root = Path(args.skills_root)
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    files = sorted(root.glob("*/tools.yaml"))
    all_problems: List[Tuple[str, str]] = []
    for file in files:
        all_problems.extend(lint_file(file))

    if all_problems:
        for rule, message in all_problems:
            print(f"[{rule}] {message}")
        print(f"\n{len(all_problems)} problem(s) found in {len(files)} file(s).", file=sys.stderr)
        return 1

    print(f"OK: {len(files)} tools.yaml files pass affinity lint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
