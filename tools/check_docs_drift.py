#!/usr/bin/env python3
"""Check docs for drift against an exported ``tools/list`` snapshot.

The checker is intentionally dumb:

* compare claimed tool counts in Markdown against the actual exported count
* flag backticked tool names that no longer exist in ``tools/list``
* warn when a tool exists in ``tools/list`` but is never referenced in docs

Input is a JSON export of ``tools/list`` plus a repo root to scan for ``*.md``.
The JSON can be produced ahead of time or generated in CI from a local server.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Set

_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_TOOL_LIKE_RE = re.compile(r"^[A-Za-z0-9_.-]*[_\.][A-Za-z0-9_.-]*$")
_COUNT_RE = re.compile(r"\b(\d+)(\+?)\s+(?:typed\s+)?(?:Maya\s+)?tools?\b", re.IGNORECASE)
_FENCE_RE = re.compile(r"^(?:```|~~~)")
_SKIP_DIRS = {".git", ".hg", ".svn", ".tox", ".venv", "build", "dist", "node_modules", "__pycache__", ".pytest_cache"}


@dataclass(frozen=True)
class CountClaim:
    path: Path
    line: int
    expected: int
    minimum: bool
    text: str


@dataclass(frozen=True)
class ToolRef:
    path: Path
    line: int
    name: str


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str
    path: Optional[Path] = None
    line: Optional[int] = None


def _is_skipped(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def _iter_markdown_files(repo_root: Path) -> Iterable[Path]:
    for path in sorted(repo_root.rglob("*.md")):
        rel = path.relative_to(repo_root)
        if _is_skipped(rel):
            continue
        yield path


def _load_tools_list(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError("tools-list JSON is empty: {}".format(path))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("tools-list JSON is invalid ({}): {}".format(path, exc)) from exc
    if isinstance(payload, list):
        tools = payload
    elif isinstance(payload, dict):
        tools = payload.get("tools")
        if tools is None and isinstance(payload.get("result"), dict):
            tools = payload["result"].get("tools")
    else:
        raise ValueError("unsupported tools-list JSON shape: {!r}".format(type(payload).__name__))

    if not isinstance(tools, list):
        raise ValueError("tools-list JSON does not contain a tools array")
    return [tool for tool in tools if isinstance(tool, dict)]


def _tool_names(tools: Sequence[dict]) -> Set[str]:
    names: Set[str] = set()
    for tool in tools:
        name = tool.get("name")
        if isinstance(name, str) and name:
            names.add(name)
    return names


def _scan_markdown(repo_root: Path, tool_names: Set[str]) -> tuple[list[CountClaim], list[ToolRef], Set[str]]:
    claims: list[CountClaim] = []
    refs: list[ToolRef] = []
    referenced: Set[str] = set()

    for path in _iter_markdown_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="replace")
        in_fence = False
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.rstrip("\n")
            stripped = line.strip()
            if _FENCE_RE.match(stripped):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            for count, plus in _COUNT_RE.findall(line):
                claims.append(
                    CountClaim(
                        path=path,
                        line=lineno,
                        expected=int(count),
                        minimum=bool(plus),
                        text=line.strip(),
                    )
                )

            for match in _INLINE_CODE_RE.finditer(line):
                token = match.group(1).strip()
                if _TOOL_LIKE_RE.match(token):
                    refs.append(ToolRef(path=path, line=lineno, name=token))
                    if token in tool_names:
                        referenced.add(token)

    return claims, refs, referenced


def check_docs_drift(repo_root: Path, tools_list_path: Path) -> list[Issue]:
    """Return human-readable issues; empty means the docs and tool list agree."""
    tools = _load_tools_list(tools_list_path)
    tool_names = _tool_names(tools)
    claims, refs, referenced = _scan_markdown(repo_root, tool_names)

    issues: list[Issue] = []
    actual = len(tool_names)

    for claim in claims:
        ok = actual >= claim.expected if claim.minimum else actual == claim.expected
        if ok:
            continue
        comparator = ">=" if claim.minimum else "=="
        issues.append(
            Issue(
                severity="error",
                code="TOOL_COUNT_MISMATCH",
                message=(
                    "{path}:{line}: claimed {expected}{plus} tools but tools/list has {actual} "
                    "({comparator} expected)"
                ).format(
                    path=claim.path.as_posix(),
                    line=claim.line,
                    expected=claim.expected,
                    plus="+" if claim.minimum else "",
                    actual=actual,
                    comparator=comparator,
                ),
                path=claim.path,
                line=claim.line,
            )
        )

    for ref in refs:
        if ref.name not in tool_names:
            issues.append(
                Issue(
                    severity="error",
                    code="STALE_TOOL_REF",
                    message="{path}:{line}: references missing tool `{name}`".format(
                        path=ref.path.as_posix(), line=ref.line, name=ref.name
                    ),
                    path=ref.path,
                    line=ref.line,
                )
            )

    undocumented = sorted(tool_names - referenced)
    if undocumented:
        sample = ", ".join(undocumented[:10])
        suffix = "" if len(undocumented) <= 10 else " ..."
        issues.append(
            Issue(
                severity="warning",
                code="UNDOCUMENTED_TOOLS",
                message=(
                    "{count} tools in tools/list are never referenced in Markdown "
                    "(sample: {sample}{suffix})"
                ).format(count=len(undocumented), sample=sample, suffix=suffix),
                path=tools_list_path,
                line=1,
            )
        )

    return issues


def _emit(issue: Issue) -> None:
    loc = ""
    if issue.path is not None:
        loc = " file={}".format(issue.path.as_posix())
        if issue.line is not None:
            loc += ",line={}".format(issue.line)
    print("::{}{}::{} [{}]".format(issue.severity, loc, issue.message, issue.code))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check docs against a tools/list export.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root to scan for Markdown files.",
    )
    parser.add_argument(
        "--tools-list",
        type=Path,
        required=True,
        help="JSON export of tools/list (either a raw tool array or a {tools: [...]} payload).",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    tools_list = args.tools_list.resolve()
    if not repo_root.is_dir():
        print("ERROR: repo root not found: {}".format(repo_root), file=sys.stderr)
        return 2
    if not tools_list.is_file():
        print("ERROR: tools-list JSON not found: {}".format(tools_list), file=sys.stderr)
        return 2

    try:
        issues = check_docs_drift(repo_root, tools_list)
    except (OSError, ValueError) as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]

    print(
        "Docs drift check: {errors} error(s), {warnings} warning(s), scanned {repo} against {tools}".format(
            errors=len(errors),
            warnings=len(warnings),
            repo=repo_root,
            tools=tools_list,
        )
    )
    for issue in issues:
        _emit(issue)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
